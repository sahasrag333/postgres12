from flask import Flask, request, jsonify
from flasgger import Swagger
from capital_group.configs import config
from capital_group.Utils.ce_logger import get_logger, ScrapedResult, SessionLocal
from capital_group.Utils.db_utils import db
logger = get_logger()

def create_app():
    """
    Flask Application Factory.
    Initializes the core application, Swagger UI, and registers blueprints.
    """
    app = Flask(__name__)
    
    # Load configurations from our central config file
    app.config.from_object(config)

    # Initialize Swagger (API Docs)
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/"
    }
    
    # We define the /results path here manually so it shows in Swagger 
    # without needing docstrings in the function.
    template = {
        "swagger": "2.0",
        "info": {
            "title": "Capital Group API",
            "description": "API Documentation for Scraping, Extraction, and Validation Services",
            "contact": {
                "responsibleOrganization": "Capital Group",
                "email": "dev-team@capgroup.com",
            },
            "version": "1.0.0"
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "paths": {
            "/results": {
                "get": {
                    "tags": ["Database"],
                    "summary": "Get all scraped results",
                    "description": "Retrieves all records stored in the SQLite database.",
                    "responses": {
                        "200": {
                            "description": "A list of scraped items",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "url": {"type": "string"},
                                        "data": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Swagger(app, config=swagger_config, template=template)

    # Database Initialization
    db.init_app(app)

    @app.route('/results', methods=['GET'])
    def get_results():
        db_session = SessionLocal()
        try:
            rows = db_session.query(ScrapedResult).all()
            output = []
            for r in rows:
                output.append({
                    "id": r.id, 
                    "url": r.url, 
                    "data": r.data
                })
            return jsonify(output)
        except Exception as e:
            logger.error(f"Error fetching results: {str(e)}")
            return jsonify({"error": str(e)}), 500
        finally:
            db_session.close()

    @app.before_request
    def log_request_info():
        logger.debug(f"Request: {request.method} {request.url}")

    # Register Blueprints (Routes)
    from capital_group.flask.views import main_bp
    app.register_blueprint(main_bp)

    logger.info("Flask Application started and Swagger UI initialized at /apidocs")

    return app