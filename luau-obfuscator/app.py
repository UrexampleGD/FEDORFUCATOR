"""Flask server exposing POST /obfuscate."""

from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from obfuscator import obfuscate

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["20 per minute", "300 per hour"],
    storage_uri="memory://",
)

MAX_SOURCE_BYTES = 64 * 1024


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/obfuscate", methods=["POST"])
@limiter.limit("5 per minute")
def obfuscate_endpoint():
    data = request.get_json(silent=True) or {}
    source = data.get("source", "")

    if not source:
        return jsonify({"ok": False, "error": "empty source"}), 400
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return jsonify({"ok": False, "error": "source too large"}), 413

    try:
        result = obfuscate(source)
        return jsonify({"ok": True, "result": result})
    except SyntaxError as e:
        return jsonify({"ok": False, "error": f"parse error: {e}"}), 400
    except NotImplementedError as e:
        return jsonify({"ok": False, "error": f"unsupported: {e}"}), 400
    except Exception:
        app.logger.exception("obfuscation failed")
        return jsonify({"ok": False, "error": "internal error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
