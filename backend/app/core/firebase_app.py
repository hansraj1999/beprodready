import json
import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_firebase() -> None:
    if firebase_admin._apps:
        return

    raw_json = (settings.FIREBASE_CREDENTIALS_JSON or "").strip()
    if raw_json:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.error("firebase.credentials_json_invalid", extra={"error": str(exc)})
            raise
        if not isinstance(info, dict):
            raise ValueError("FIREBASE_CREDENTIALS_JSON must be a JSON object")
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred)
        logger.info("firebase.initialized", extra={"mode": "credentials_json"})
        return

    path = settings.FIREBASE_CREDENTIALS_PATH
    if path:
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
        logger.info("firebase.initialized", extra={"mode": "certificate_path"})
        return

    firebase_admin.initialize_app()
    logger.info("firebase.initialized", extra={"mode": "application_default"})


def shutdown_firebase() -> None:
    if not firebase_admin._apps:
        return
    app = firebase_admin.get_app()
    firebase_admin.delete_app(app)
    logger.info("firebase.shutdown")
