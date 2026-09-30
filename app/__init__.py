from __future__ import annotations

import logging, time, uuid
from flask import Flask, Blueprint, g, jsonify, request
from werkzeug.exceptions import HTTPException
from app.auth import require_api_key
from app.database.connection import TransactionManager
from app.errors import AppError
from app.kafka import KafkaEventProducer
from app.settings import Settings


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_environment()
    logging.basicConfig(level=settings.log_level)
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.flask_secret_key
    transactions, events = TransactionManager(settings.database_url), KafkaEventProducer(settings.kafka_bootstrap_servers, settings.kafka_client_id, settings.kafka_topic)
    api = Blueprint("api", __name__, url_prefix="/api/v1")
    api.before_request(require_api_key(settings.api_keys)(lambda: None))
    from app.repositories.members import MemberRepository
    from app.services.members import MemberService
    from app.controllers.members import register_routes as member_routes
    from app.repositories.trainers import TrainerRepository
    from app.services.trainers import TrainerService
    from app.controllers.trainers import register_routes as trainer_routes
    from app.repositories.memberships import MembershipRepository
    from app.services.memberships import MembershipService
    from app.controllers.memberships import create_memberships_blueprint
    member_routes(api, MemberService(transactions, MemberRepository(), events))
    trainer_routes(api, TrainerService(transactions, TrainerRepository()))
    membership_bp = create_memberships_blueprint(MembershipService(transactions, MembershipRepository(), events))
    membership_bp.before_request(require_api_key(settings.api_keys)(lambda: None))
    app.register_blueprint(api)
    app.register_blueprint(membership_bp, url_prefix="/api/v1")
    # Attendance blueprint is constructed around a connection-backed repository.
    from app.repositories.attendance import AttendanceRepository
    from app.services.attendance import AttendanceService
    from app.controllers.attendance import create_attendance_blueprint
    with transactions.transaction() as connection:
        attendance_bp = create_attendance_blueprint(AttendanceService(AttendanceRepository(connection), events))
    attendance_bp.before_request(require_api_key(settings.api_keys)(lambda: None))
    app.register_blueprint(attendance_bp, url_prefix="/api/v1")

    @app.before_request
    def request_context() -> None:
        g.correlation_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or str(uuid.uuid4()); g.started_at = time.monotonic()
    @app.after_request
    def log_response(response):
        app.logger.info("request completed method=%s path=%s status=%s duration_ms=%d correlation_id=%s", request.method, request.path, response.status_code, int((time.monotonic()-g.get('started_at',time.monotonic()))*1000), g.get("correlation_id")); return response
    def error_response(error: AppError):
        body={"error":{"code":error.code,"message":error.message,"timestamp":__import__('datetime').datetime.now(__import__('datetime').UTC).isoformat(),"correlation_id":g.get("correlation_id")}}
        if error.details: body["error"]["details"]=error.details
        return jsonify(body), error.status_code
    app.register_error_handler(AppError, error_response)
    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException): return jsonify({"error":{"code":"http_error","message":error.description,"timestamp":__import__('datetime').datetime.now(__import__('datetime').UTC).isoformat(),"correlation_id":g.get("correlation_id")}}), error.code
    @app.errorhandler(Exception)
    def unexpected(error: Exception): app.logger.exception("unhandled request error correlation_id=%s",g.get("correlation_id")); return jsonify({"error":{"code":"internal_error","message":"An unexpected error occurred","timestamp":__import__('datetime').datetime.now(__import__('datetime').UTC).isoformat(),"correlation_id":g.get("correlation_id")}}),500
    @app.get("/health")
    def health(): return {"status":"ok"}
    from app.openapi import openapi_document, docs_html
    @app.get("/openapi.json")
    def openapi(): return jsonify(openapi_document())
    @app.get("/docs")
    def docs(): return docs_html()
    return app
