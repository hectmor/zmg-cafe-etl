"""FastAPI application exposing only the consumer-facing analytics layer."""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Query

from .db import AnalyticsStore, StoreError
from .schemas import Cafe, CafeList, Health, Stats, cafe_from_row, feature_collection


def get_store() -> AnalyticsStore:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return AnalyticsStore(dsn)


def create_app() -> FastAPI:
    app = FastAPI(title="ZMG Cafés API", version="0.1.0")

    @app.get("/health", response_model=Health)
    def health(store: AnalyticsStore = Depends(get_store)) -> Health:
        if not store.ping():
            raise HTTPException(status_code=503, detail="database is unreachable")
        return Health(status="ok", database="connected")

    @app.get("/cafes", response_model=CafeList)
    def list_cafes(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        store: AnalyticsStore = Depends(get_store),
    ) -> CafeList:
        try:
            rows = store.list_cafes(limit=limit, offset=offset)
            total = store.count_cafes()
        except StoreError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return CafeList(
            total=total,
            limit=limit,
            offset=offset,
            items=[cafe_from_row(row) for row in rows],
        )

    @app.get("/cafes/{source_id}", response_model=Cafe)
    def get_cafe(source_id: str, store: AnalyticsStore = Depends(get_store)) -> Cafe:
        try:
            row = store.get_cafe(source_id)
        except StoreError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        if row is None:
            raise HTTPException(status_code=404, detail="cafe not found")
        return cafe_from_row(row)

    @app.get("/geojson/cafes")
    def cafes_geojson(
        limit: int = Query(1000, ge=1, le=5000),
        offset: int = Query(0, ge=0),
        store: AnalyticsStore = Depends(get_store),
    ) -> dict[str, object]:
        try:
            rows = store.list_cafes(limit=limit, offset=offset)
        except StoreError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return feature_collection(rows)

    @app.get("/stats", response_model=Stats)
    def stats(store: AnalyticsStore = Depends(get_store)) -> Stats:
        try:
            return Stats(**store.stats())
        except StoreError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return app


app = create_app()
