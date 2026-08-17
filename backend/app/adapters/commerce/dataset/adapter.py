import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import NAMESPACE_URL, uuid5
from packaging.version import InvalidVersion, Version

from pydantic import ValidationError

from app.adapters.commerce.base import AdapterContext, AdapterError, AdapterResult
from app.adapters.commerce.dataset.base_mapper import (
    PlatformDatasetMapper,
    ProductMappingContext,
)
from app.adapters.commerce.dataset.mappers import (
    AmazonDatasetMapper,
)
from app.modules.market_intelligence.schemas import (
    AdapterCapabilities,
    AnalysisScope,
    CollectionRun,
    CollectionStatus,
    DataLevel,
    DataSourceMode,
    DataStatus,
    DatasetManifest,
    DatasetSourceType,
    EvidenceReference,
    NormalizedProduct,
    ProductSearchRequest,
    ProductSort,
)


DEFAULT_DATASET_ROOT = (
    Path(__file__).resolve().parents[4] / "data" / "market_intelligence"
)
PRODUCT_FILE_NAMES = ("products.json", "products.jsonl")


@dataclass(frozen=True)
class DatasetSelection:
    dataset_dir: Path
    product_path: Path
    manifest: DatasetManifest


@dataclass(frozen=True)
class MappedProductRecord:
    product: NormalizedProduct
    record_number: int


class DatasetAdapter:
    data_source_mode = DataSourceMode.FIXED_DATASET.value
    adapter_version = "dataset-adapter-v1"
    schema_version = "1.0"
    max_products = 50

    def __init__(
        self,
        platform: str,
        *,
        dataset_root: str | Path = DEFAULT_DATASET_ROOT,
        mappers: Iterable[PlatformDatasetMapper] | None = None,
        dataset_permissions: Mapping[str, Iterable[str]] | None = None,
        public_dataset_ids: Iterable[str] | None = None,
    ) -> None:
        normalized_platform = self._selector(platform)
        if not normalized_platform:
            raise ValueError("platform is required")
        self.platform = normalized_platform
        self.dataset_root = Path(dataset_root).resolve()
        self._mappers = self._build_mapper_registry(mappers)
        if self.platform not in self._mappers:
            raise ValueError(f"dataset mapper is not registered: {self.platform}")
        self._dataset_permissions = {
            dataset_id: frozenset(tenant_ids)
            for dataset_id, tenant_ids in (dataset_permissions or {}).items()
        }
        self._public_dataset_ids = frozenset(public_dataset_ids or ())

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            platform=self.platform,
            data_source_mode=self.data_source_mode,
            supports_products=True,
            supports_reviews=False,
            supports_market_metrics=False,
            max_products=self.max_products,
            max_reviews_per_product=0,
            adapter_version=self.adapter_version,
            schema_version=self.schema_version,
        )

    def search_products(
        self,
        request: ProductSearchRequest,
        context: AdapterContext,
    ) -> AdapterResult[list[NormalizedProduct]]:
        request = self._validate_request(request)
        run = CollectionRun(
            task_id=context.task_id,
            trace_id=context.trace_id,
            tenant_id=context.tenant_id,
            keyword=request.keyword,
            requested_count=request.product_limit,
            status=CollectionStatus.RUNNING,
            adapter_version=self.adapter_version,
        )
        try:
            if self._selector(request.platform) != self.platform:
                raise AdapterError(
                    "UNSUPPORTED_DATA_SOURCE",
                    f"DatasetAdapter supports platform={self.platform}.",
                )
            selection = self._find_dataset(request)
            self._validate_access(selection.manifest, context)
            mapper = self._mappers[self.platform]
            if not mapper.supports_sort(request.sort_by):
                raise AdapterError(
                    "UNSUPPORTED_SORT",
                    f"Dataset mapper for {self.platform} does not support "
                    f"sort_by={request.sort_by.value}.",
                )

            dataset_files = self._read_validated_dataset_files(selection)
            dataset_bytes = dataset_files[selection.product_path.name]
            dataset_sha256 = hashlib.sha256(dataset_bytes).hexdigest()
            data_status = self._data_status(selection.manifest)
            raw_records = self._parse_records(dataset_bytes, selection.product_path)
            mapped_records, warnings = self._map_products(
                raw_records,
                mapper,
                selection,
                run.id,
                data_status,
            )
            if data_status is DataStatus.STALE:
                warnings.append("DATASET_STALE")

            mapped_records = self._sort_products(
                mapped_records,
                request.sort_by,
            )
            mapped_records = mapped_records[: request.product_limit]

            if not mapped_records:
                raise AdapterError(
                    "DATA_EMPTY",
                    "The selected dataset contains no usable products.",
                )

            insufficient_count = (
                len(mapped_records) < request.product_limit
            )

            has_row_warnings = any(
                warning.startswith(
                    (
                        "ROW_SKIPPED:",
                        "DUPLICATE_PRODUCT_SKIPPED:",
                    )
                )
                for warning in warnings
            )

            status = (
                CollectionStatus.PARTIAL
                if insufficient_count or has_row_warnings
                else CollectionStatus.COMPLETED
            )

            if insufficient_count:
                stop_reason = "REQUESTED_COUNT_NOT_REACHED"
            elif has_row_warnings:
                stop_reason = "SOURCE_ROWS_SKIPPED"
            else:
                stop_reason = None
            run = run.model_copy(
                update={
                    "actual_count": len(mapped_records),
                    "status": status,
                    "stop_reason": stop_reason,
                    "finished_at": datetime.now(UTC),
                }
            )
            scope = self._analysis_scope(
                request,
                selection.manifest,
                len(mapped_records),
            )
            evidence_refs = [
                self._build_evidence(
                    mapped_record=mapped_record,
                    context=context,
                    request=request,
                    run=run,
                    scope=scope,
                    manifest=selection.manifest,
                    dataset_sha256=dataset_sha256,
                )
                for mapped_record in mapped_records
            ]
            return AdapterResult(
                data=[record.product for record in mapped_records],
                run=run,
                evidence_refs=evidence_refs,
                warnings=warnings,
                degraded=status is CollectionStatus.PARTIAL,
            )
        except AdapterError as exc:
            failed_run = run.model_copy(
                update={
                    "status": CollectionStatus.FAILED,
                    "stop_reason": exc.code,
                    "finished_at": datetime.now(UTC),
                }
            )
            exc.collection_run_id = run.id
            exc.run = failed_run
            raise

    def _find_dataset(self, request: ProductSearchRequest) -> DatasetSelection:
        if not self.dataset_root.is_dir():
            raise AdapterError(
                "DATA_SOURCE_DISABLED",
                f"Dataset root does not exist: {self.dataset_root.name}.",
            )
        matches: list[DatasetSelection] = []
        try:
            dataset_dirs = sorted(
                path for path in self.dataset_root.iterdir() if path.is_dir()
            )
        except OSError as exc:
            raise AdapterError(
                "COLLECTION_INTERNAL_ERROR",
                "Dataset root cannot be read.",
                retryable=True,
            ) from exc

        for dataset_dir in dataset_dirs:
            manifest_path = dataset_dir / "manifest.json"
            if not manifest_path.is_file():
                continue

            manifest = self._load_manifest(manifest_path)

            print("MANIFEST:", (
                manifest.platform,
                manifest.market,
                manifest.category,
                manifest.keyword,
            ))

            print("REQUEST:", (
                request.platform,
                request.market,
                request.category,
                request.keyword,
            ))

            if not self._manifest_matches(manifest, request):
                continue
            matches.append(
                DatasetSelection(
                    dataset_dir=dataset_dir,
                    product_path=self._product_path(dataset_dir, manifest),
                    manifest=manifest,
                )
            )
        if not matches:
            raise AdapterError(
                "DATA_EMPTY",
                "No fixed dataset matches the request.",
            )

        try:
            matches.sort(
                key=lambda item: Version(
                    item.manifest.dataset_version
                ),
                reverse=True,
            )
        except InvalidVersion as exc:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                "Dataset version must use a valid version format.",
            ) from exc

        return matches[0]

    def _load_manifest(self, manifest_path: Path) -> DatasetManifest:
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Dataset manifest contains invalid JSON: {manifest_path.parent.name}.",
            ) from exc
        except OSError as exc:
            raise AdapterError(
                "COLLECTION_INTERNAL_ERROR",
                f"Dataset manifest cannot be read: {manifest_path.parent.name}.",
                retryable=True,
            ) from exc
        try:
            manifest = DatasetManifest.model_validate(raw)
        except ValidationError as exc:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Dataset manifest is invalid: {self._error_summary(exc)}.",
            ) from exc
        if manifest.schema_version != self.schema_version:
            raise AdapterError(
                "SCHEMA_VERSION_UNSUPPORTED",
                f"Unsupported dataset schema version: {manifest.schema_version}.",
            )
        return manifest

    def _validate_access(
        self,
        manifest: DatasetManifest,
        context: AdapterContext,
    ) -> None:
        if manifest.dataset_id in self._public_dataset_ids:
            return
        allowed_tenants = self._dataset_permissions.get(manifest.dataset_id, frozenset())
        if context.tenant_id not in allowed_tenants:
            raise AdapterError(
                "TOOL_PERMISSION_DENIED",
                "The tenant is not authorized to use this fixed dataset.",
            )

    def _product_path(
        self,
        dataset_dir: Path,
        manifest: DatasetManifest,
    ) -> Path:
        product_names = [
            name for name in PRODUCT_FILE_NAMES if name in manifest.checksums
        ]
        if not product_names:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                "Dataset manifest does not declare a product file checksum.",
            )
        if len(product_names) > 1:
            raise AdapterError(
                "DATA_CONFLICT",
                "Dataset manifest declares multiple product files.",
            )
        product_path = dataset_dir / product_names[0]
        if not product_path.is_file():
            raise AdapterError(
                "DATA_SOURCE_DISABLED",
                f"Dataset product file does not exist: {product_names[0]}.",
            )
        return product_path

    @staticmethod
    def _read_file(path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise AdapterError(
                "COLLECTION_INTERNAL_ERROR",
                f"Dataset file cannot be read: {path.name}.",
                retryable=True,
            ) from exc

    def _read_validated_dataset_files(
        self,
        selection: DatasetSelection,
    ) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for file_name in sorted(selection.manifest.checksums):
            if Path(file_name).name != file_name:
                raise AdapterError(
                    "SCHEMA_VALIDATION_FAILED",
                    f"Manifest contains an invalid dataset file name: {file_name}.",
                )
            path = selection.dataset_dir / file_name
            if not path.is_file():
                raise AdapterError(
                    "DATA_SOURCE_DISABLED",
                    f"Dataset file does not exist: {file_name}.",
                )
            content = self._read_file(path)
            actual_sha256 = hashlib.sha256(content).hexdigest()
            self._validate_checksum(selection.manifest, path, actual_sha256)
            files[file_name] = content
        return files

    @staticmethod
    def _validate_checksum(
        manifest: DatasetManifest,
        path: Path,
        actual_sha256: str,
    ) -> None:
        expected_sha256 = manifest.checksums.get(path.name)
        if expected_sha256 is None:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Manifest checksum is missing for {path.name}.",
            )
        if expected_sha256.casefold() != actual_sha256.casefold():
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Dataset checksum does not match manifest: {path.name}.",
            )

    def _parse_records(
        self,
        dataset_bytes: bytes,
        path: Path,
    ) -> list[tuple[int, Mapping[str, Any]]]:
        try:
            text = dataset_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Dataset file is not valid UTF-8: {path.name}.",
            ) from exc
        if path.suffix.casefold() == ".jsonl":
            return self._parse_jsonl(text, path)
        return self._parse_json_array(text, path)

    @staticmethod
    def _parse_jsonl(
        text: str,
        path: Path,
    ) -> list[tuple[int, Mapping[str, Any]]]:
        records: list[tuple[int, Mapping[str, Any]]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AdapterError(
                    "SCHEMA_VALIDATION_FAILED",
                    f"Invalid JSON at {path.name}:{line_number}.",
                ) from exc
            if not isinstance(raw, dict):
                raise AdapterError(
                    "SCHEMA_VALIDATION_FAILED",
                    f"Expected an object at {path.name}:{line_number}.",
                )
            records.append((line_number, raw))
        return records

    @staticmethod
    def _parse_json_array(
        text: str,
        path: Path,
    ) -> list[tuple[int, Mapping[str, Any]]]:
        try:
            raw_records = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Dataset file contains invalid JSON: {path.name}.",
            ) from exc
        if not isinstance(raw_records, list):
            raise AdapterError(
                "SCHEMA_VALIDATION_FAILED",
                f"Expected a JSON array in {path.name}.",
            )
        records: list[tuple[int, Mapping[str, Any]]] = []
        for index, raw in enumerate(raw_records, start=1):
            if not isinstance(raw, dict):
                raise AdapterError(
                    "SCHEMA_VALIDATION_FAILED",
                    f"Expected an object at {path.name} index {index}.",
                )
            records.append((index, raw))
        return records

    def _map_products(
        self,
        raw_records: list[tuple[int, Mapping[str, Any]]],
        mapper: PlatformDatasetMapper,
        selection: DatasetSelection,
        collection_run_id: str,
        data_status: DataStatus,
    ) -> tuple[list[MappedProductRecord], list[str]]:
        mapped_records: list[MappedProductRecord] = []
        warnings: list[str] = []
        seen_product_ids: set[str] = set()
        for record_number, raw in raw_records:
            mapping_context = ProductMappingContext(
                collection_run_id=collection_run_id,
                manifest=selection.manifest,
                source_timestamp=selection.manifest.source_timestamp,
                data_status=data_status,
                source_snapshot_ref=self._snapshot_ref(
                    selection,
                    record_number,
                ),
            )
            try:
                product = mapper.map_product(raw, mapping_context)
            except (TypeError, ValueError, ValidationError) as exc:
                warnings.append(
                    f"ROW_SKIPPED:{record_number}:{self._error_summary(exc)}"
                )
                continue
            if product.product_id in seen_product_ids:
                warnings.append(
                    f"DUPLICATE_PRODUCT_SKIPPED:{record_number}:{product.product_id}"
                )
                continue
            mapped_records.append(
                MappedProductRecord(
                    product=product,
                    record_number=record_number,
                )
            )
            seen_product_ids.add(product.product_id)
        return mapped_records, warnings

    @staticmethod
    def _sort_products(
        records: list[MappedProductRecord],
        sort_by: ProductSort,
    ) -> list[MappedProductRecord]:
        if sort_by is ProductSort.PRICE_ASC:
            return sorted(records, key=lambda item: item.product.price)
        if sort_by is ProductSort.PRICE_DESC:
            return sorted(records, key=lambda item: item.product.price, reverse=True)
        if sort_by is ProductSort.SALES_DESC:
            return sorted(
                records,
                key=lambda item: (
                    item.product.sales_value is not None,
                    item.product.sales_value or 0,
                ),
                reverse=True,
            )
        return records

    def _build_evidence(
        self,
        *,
        mapped_record: MappedProductRecord,
        context: AdapterContext,
        request: ProductSearchRequest,
        run: CollectionRun,
        scope: AnalysisScope,
        manifest: DatasetManifest,
        dataset_sha256: str,
    ) -> EvidenceReference:
        product = mapped_record.product
        evidence_key = (
            f"{manifest.dataset_id}:{manifest.dataset_version}:"
            f"{dataset_sha256}:{product.product_id}:{mapped_record.record_number}"
        )
        return EvidenceReference(
            evidence_id=str(uuid5(NAMESPACE_URL, evidence_key)),
            evidence_type="product",
            data_level=self._data_level(manifest),
            data_source=manifest.source_description,
            platform=product.platform,
            product_id=product.product_id,
            query_range={
                "market": request.market,
                "category": request.category,
                "keyword": request.keyword,
                "product_limit": request.product_limit,
                "sort_by": request.sort_by.value,
                "record_number": mapped_record.record_number,
                "dataset_id": manifest.dataset_id,
            },
            source_timestamp=product.source_timestamp,
            ingest_timestamp=product.ingest_timestamp,
            tool_call_id=context.tool_call_id,
            collection_run_id=run.id,
            snapshot_ref=product.source_snapshot_ref,
            sha256=dataset_sha256,
            data_version=manifest.dataset_version,
            sample_scope=scope,
        )

    @staticmethod
    def _analysis_scope(
        request: ProductSearchRequest,
        manifest: DatasetManifest,
        actual_count: int,
    ) -> AnalysisScope:
        return AnalysisScope(
            market=manifest.market.upper(),
            platforms=[manifest.platform.lower()],
            category=manifest.category,
            keyword=manifest.keyword,
            start_time=None,
            end_time=manifest.source_timestamp,
            requested_product_count=request.product_limit,
            actual_product_count=actual_count,
            actual_review_count=0,
            data_source_mode=DataSourceMode.FIXED_DATASET,
        )

    def _manifest_matches(
        self,
        manifest: DatasetManifest,
        request: ProductSearchRequest,
    ) -> bool:
        return (
            self._selector(manifest.platform) == self.platform
            and self._selector(request.platform) == self.platform
            and self._selector(manifest.market) == self._selector(request.market)
            and self._selector(manifest.category) == self._selector(request.category)
            and self._selector(manifest.keyword) == self._selector(request.keyword)
        )

    @staticmethod
    def _data_status(manifest: DatasetManifest) -> DataStatus:
        if manifest.expires_at is not None and manifest.expires_at <= datetime.now(UTC):
            return DataStatus.STALE
        if manifest.source_type is DatasetSourceType.AUTHORIZED_EXPORT:
            return DataStatus.VALID
        return DataStatus.DEMO_ONLY

    @staticmethod
    def _data_level(manifest: DatasetManifest) -> DataLevel:
        if manifest.source_type is DatasetSourceType.AUTHORIZED_EXPORT:
            return DataLevel.A
        return DataLevel.D

    @staticmethod
    def _validate_request(request: ProductSearchRequest) -> ProductSearchRequest:
        try:
            return ProductSearchRequest.model_validate(request, from_attributes=True)
        except ValidationError as exc:
            raise AdapterError(
                "INVALID_ARGUMENT",
                DatasetAdapter._error_summary(exc),
            ) from exc

    @staticmethod
    def _build_mapper_registry(
        mappers: Iterable[PlatformDatasetMapper] | None,
    ) -> dict[str, PlatformDatasetMapper]:
        mapper_instances = list(
            mappers
            or (
                AmazonDatasetMapper(),
            )
        )
        registry: dict[str, PlatformDatasetMapper] = {}
        for mapper in mapper_instances:
            key = DatasetAdapter._selector(mapper.platform)
            if not key:
                raise ValueError("dataset mapper platform is required")
            if key in registry:
                raise ValueError(f"dataset mapper already registered: {key}")
            registry[key] = mapper
        return registry

    @staticmethod
    def _snapshot_ref(
        selection: DatasetSelection,
        record_number: int,
    ) -> str:
        marker = "L" if selection.product_path.suffix.casefold() == ".jsonl" else "I"
        return (
            f"{selection.manifest.dataset_id}/{selection.product_path.name}"
            f"#{marker}{record_number}"
        )

    @staticmethod
    def _selector(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _error_summary(error: Exception) -> str:
        if isinstance(error, ValidationError):
            first = error.errors()[0]
            return str(first.get("msg", "schema validation failed"))
        return str(error) or error.__class__.__name__
