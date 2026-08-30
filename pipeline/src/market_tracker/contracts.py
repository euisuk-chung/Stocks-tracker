from __future__ import annotations

from typing import Any

from .models import SCHEMA_VERSION


def json_schemas() -> dict[str, dict[str, Any]]:
    string_array = {"type": "array", "items": {"type": "string"}}
    return {
        "market-snapshot.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "market-snapshot.schema.json",
            "title": "MarketSnapshot",
            "type": "object",
            "required": [
                "schemaVersion", "marketDate", "capturedAt", "source", "universe", "securities",
                "gainers", "losers", "deepDiveSymbols", "marketEtfs", "incomeBasket",
                "nasdaqRegime", "sectorHeatmap", "inputHash",
            ],
            "properties": {
                "schemaVersion": {"const": SCHEMA_VERSION},
                "marketDate": {"type": "string", "format": "date"},
                "capturedAt": {"type": "string", "format": "date-time"},
                "source": {"type": "string"},
                "universe": string_array,
                "securities": {"type": "array", "items": {"type": "object"}},
                "gainers": {"type": "array", "minItems": 10, "maxItems": 10, "items": {"type": "object"}},
                "losers": {"type": "array", "minItems": 10, "maxItems": 10, "items": {"type": "object"}},
                "deepDiveSymbols": {**string_array, "minItems": 6, "maxItems": 6, "uniqueItems": True},
                "marketEtfs": string_array,
                "incomeBasket": string_array,
                "nasdaqRegime": {"type": "object"},
                "sectorHeatmap": {"type": "array", "items": {"type": "object"}},
                "inputHash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
            "additionalProperties": False,
        },
        "evidence-ledger.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "evidence-ledger.schema.json",
            "title": "EvidenceLedger",
            "type": "object",
            "required": ["schemaVersion", "marketDate", "sources", "evidence", "themes"],
            "properties": {
                "schemaVersion": {"const": SCHEMA_VERSION},
                "marketDate": {"type": "string", "format": "date"},
                "sources": {"type": "array", "items": {"type": "object"}},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "themes": {"type": "array", "maxItems": 3, "items": {"type": "object"}},
            },
            "additionalProperties": False,
        },
        "review-result.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "review-result.schema.json",
            "title": "ReviewResult",
            "type": "object",
            "required": ["reviewer", "verdict", "blockingIssues", "improvements", "checkedItems", "reviewedAt"],
            "properties": {
                "reviewer": {"type": "string"},
                "verdict": {"enum": ["pass", "revise", "block"]},
                "blockingIssues": {"type": "array", "items": {"type": "object"}},
                "improvements": {"type": "array", "items": {"type": "object"}},
                "checkedItems": string_array,
                "reviewedAt": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        },
        "daily-report.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "daily-report.schema.json",
            "title": "DailyReport",
            "type": "object",
            "required": [
                "metadata", "leadStory", "marketPulse", "nasdaqRegime", "sectorHeatmap", "movers",
                "themes", "marketEtfs", "incomeBasket", "sources", "sourceIds", "reviews", "qa", "nextWatch", "disclaimer",
            ],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["schemaVersion", "marketDate", "capturedAt", "generatedAt", "snapshotHash", "language", "educationalOnly"],
                    "properties": {
                        "schemaVersion": {"const": SCHEMA_VERSION},
                        "marketDate": {"type": "string", "format": "date"},
                        "capturedAt": {"type": "string", "format": "date-time"},
                        "generatedAt": {"type": "string", "format": "date-time"},
                        "snapshotHash": {"type": "string"},
                        "language": {"const": "ko-KR"},
                        "educationalOnly": {"const": True},
                    },
                },
                "leadStory": {
                    "type": "object",
                    "required": ["headline", "takeaway", "supportingPoints"],
                    "properties": {
                        "headline": {"type": "string", "minLength": 1},
                        "takeaway": {"type": "string", "minLength": 1},
                        "supportingPoints": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "required": ["role", "text", "claimIds"],
                                "properties": {
                                    "role": {"enum": ["market", "sector", "catalyst"]},
                                    "text": {"type": "string", "minLength": 1},
                                    "claimIds": string_array,
                                },
                                "additionalProperties": False,
                            },
                        },
                    },
                    "additionalProperties": False,
                },
                "marketPulse": {**string_array, "minItems": 3, "maxItems": 3},
                "nasdaqRegime": {"type": "object"},
                "sectorHeatmap": {"type": "array", "items": {"type": "object"}},
                "movers": {"type": "array", "minItems": 20, "maxItems": 20, "items": {"type": "object"}},
                "themes": {"type": "array", "maxItems": 3, "items": {"type": "object"}},
                "marketEtfs": {"type": "array", "minItems": 4, "items": {"type": "object"}},
                "incomeBasket": {"type": "array", "items": {"type": "object"}},
                "sources": {"type": "array", "items": {"type": "object"}},
                "sourceIds": string_array,
                "reviews": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "object"}},
                "qa": {
                    "type": "object",
                    "required": ["publishable", "reviewerStatuses", "validationErrors", "revisionCount"],
                    "properties": {
                        "publishable": {"type": "boolean"},
                        "reviewerStatuses": {
                            "type": "object",
                            "required": ["fact_checker", "blog_quality_reviewer", "humanify_reviewer"],
                        },
                        "validationErrors": string_array,
                        "revisionCount": {"type": "integer", "minimum": 0, "maximum": 2},
                    },
                },
                "nextWatch": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "required": ["title", "description", "symbols", "claimIds"],
                        "properties": {
                            "title": {"type": "string", "minLength": 1},
                            "description": {"type": "string", "minLength": 1},
                            "symbols": string_array,
                            "claimIds": string_array,
                        },
                        "additionalProperties": False,
                    },
                },
                "disclaimer": {"type": "string"},
            },
            "additionalProperties": False,
        },
    }
