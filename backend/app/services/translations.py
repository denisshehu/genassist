from typing import List

from fastapi_cache.coder import PickleCoder
from fastapi_cache.decorator import cache
from injector import inject

from app.cache.redis_cache import make_key_builder, invalidate_cache
from app.core.exceptions.error_messages import ErrorKey
from app.core.exceptions.exception_classes import AppException
from app.repositories.translations import TranslationsRepository
from app.schemas.translation import (
    TranslationCreate,
    TranslationRead,
    TranslationUpdate,
)


translation_key_builder = make_key_builder("key")  # type: ignore[assignment]
translation_all_key_builder = make_key_builder("-")  # type: ignore[assignment]


@inject
class TranslationsService:
    def __init__(self, repository: TranslationsRepository):
        self.repository = repository

    async def create(self, dto: TranslationCreate) -> TranslationRead:
        existing = await self.repository.get_by_key(dto.key)
        if existing:
            raise AppException(
                status_code=400, error_key=ErrorKey.CUSTOMER_ALREADY_EXISTS
            )
        row = await self.repository.create(dto)
        # Invalidate cached list so next read sees the new translation
        await invalidate_cache("translations:get_all", None)
        return TranslationRead.model_validate(row, from_attributes=True)

    @cache(
        expire=300,
        namespace="translations:get_all",
        key_builder=translation_all_key_builder,
        coder=PickleCoder,
    )
    async def get_all(self) -> List[TranslationRead]:
        rows = await self.repository.get_all()
        return [TranslationRead.model_validate(r, from_attributes=True) for r in rows]

    async def get_by_key(self, key: str) -> TranslationRead:
        # Read-through from the cached list returned by get_all
        rows = await self.get_all()
        for r in rows:
            if r.key == key:
                return r
        raise AppException(status_code=404, error_key=ErrorKey.NOT_FOUND)

    async def update(self, key: str, dto: TranslationUpdate) -> TranslationRead:
        existing = await self.repository.get_by_key(key)
        if not existing:
            raise AppException(status_code=404, error_key=ErrorKey.NOT_FOUND)
        updated = await self.repository.update(key, dto)
        # Invalidate cached list so next read sees the updated translation
        await invalidate_cache("translations:get_all", None)
        return TranslationRead.model_validate(updated, from_attributes=True)

    async def delete(self, key: str) -> None:
        existing = await self.repository.get_by_key(key)
        if not existing:
            raise AppException(status_code=404, error_key=ErrorKey.NOT_FOUND)
        await self.repository.delete(key)
        # Invalidate cached list so next read does not return the deleted translation
        await invalidate_cache("translations:get_all", None)
