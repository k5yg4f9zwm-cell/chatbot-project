import os
from flask import Flask, g, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from chatbot import service

csrf = CSRFProtect()


def create_app(config=None):
    app = Flask(__name__, template_folder="../templates", instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        DATABASE=os.path.join(app.instance_path, "chatbot.sqlite"),
        BACKUP=os.path.join(app.instance_path, "chatbot_backup.sqlite")
    )

    if config:
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)
    csrf.init_app(app)

    def get_db():
        if "db" not in g:
            g.db = service.connect(app.config["DATABASE"])
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/")
    def index():
        db = get_db()
        faqs = service.get_all_faqs(db)
        return render_template("index.html", faqs=faqs, results=None)

    @app.post("/search")
    def search():
        db = get_db()
        query = request.form.get("query", "")
        try:
            results = service.search_faq(db, query)
        except service.ChatbotError as err:
            flash(str(err))
            results = []
        faqs = service.get_all_faqs(db)
        return render_template("index.html", faqs=faqs, results=results, query=query)

    @app.route("/admin", methods=["GET", "POST"])
    def admin_login():
        db = get_db()
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if service.verify_admin(db, username, password):
                session["admin"] = username
                flash("Админ панеліне қош келдіңіз!")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Қате логин немесе құпия сөз!")
        return render_template("admin_login.html")

    @app.get("/admin/dashboard")
    def admin_dashboard():
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        db = get_db()
        faqs = service.get_all_faqs(db)
        logs = service.get_logs(db)
        return render_template("admin_dashboard.html", faqs=faqs, logs=logs)

    @app.post("/admin/faq/add")
    def admin_add_faq():
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        db = get_db()
        try:
            service.add_faq(
                db,
                request.form.get("question"),
                request.form.get("answer"),
                request.form.get("category")
            )
            flash("Жаңа FAQ сәтті қосылды!")
        except service.ChatbotError as err:
            flash(f"Қате: {err}")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/faq/delete/<int:faq_id>")
    def admin_delete_faq(faq_id):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        db = get_db()
        try:
            service.delete_faq(db, faq_id)
            flash("FAQ өшірілді!")
        except service.ChatbotError as err:
            flash(f"Қате: {err}")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/backup")
    def admin_backup():
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        db_path = app.config["DATABASE"]
        backup_path = app.config["BACKUP"]
        try:
            service.backup_database(db_path, backup_path)
            flash("Дерекқордың сақтық көшірмесі сәтті жасалды!")
        except service.ChatbotError as err:
            flash(f"Қате: {err}")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/restore")
    def admin_restore():
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        db_path = app.config["DATABASE"]
        backup_path = app.config["BACKUP"]
        try:
            service.restore_database(backup_path, db_path)
            flash("Дерекқор сақтық көшірмеден сәтті қалпына келтірілді!")
        except service.ChatbotError as err:
            flash(f"Қате: {err}")
        return redirect(url_for("admin_dashboard"))

    @app.get("/admin/logout")
    def admin_logout():
        session.pop("admin", None)
        flash("Жүйеден шықтыңыз.")
        return redirect(url_for("index"))

    return app