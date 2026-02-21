from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, jsonify

import markdown2
import os
from slugify import slugify
from datetime import datetime
import numpy
import bcrypt
from dotenv import load_dotenv
import platform

# config
load_dotenv()

raw = os.getenv("HASHED_PSW")

# Eğer env yanlışlıkla b"..." olarak geldiyse temizle
if raw.startswith('b"') or raw.startswith("b'"):
    raw = raw[2:-1]

HASHED_PSW = raw.encode("utf-8")

app = Flask(__name__, template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, "posts")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
NOTES_DIR = os.path.join(BASE_DIR, "notes")

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(NOTES_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {"md"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS and filename


# ── Kategori Yardımcıları ──────────────────────────────────────

def get_categories(base_dir):
    """Bir dizindeki tüm kategori klasörlerini döndürür."""
    categories = []
    for name in os.listdir(base_dir):
        full_path = os.path.join(base_dir, name)
        if os.path.isdir(full_path):
            categories.append(name)
    categories.sort()
    return categories


def get_category_keywords(base_dir, category):
    """Kategori config.txt'den anahtar kelimeleri okur."""
    config_path = os.path.join(base_dir, category, "config.txt")
    if not os.path.exists(config_path):
        return []
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    keywords = [line.strip() for line in lines if line.strip()]
    return keywords


def ensure_category_dir(base_dir, category, keywords_text=""):
    """Kategori klasörünü ve config.txt'yi oluşturur (yoksa)."""
    cat_dir = os.path.join(base_dir, category)
    os.makedirs(cat_dir, exist_ok=True)

    config_path = os.path.join(cat_dir, "config.txt")
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(keywords_text.strip() + "\n")


def find_item_category(base_dir, slug):
    """Slug'a göre dosyanın hangi kategoride olduğunu bulur."""
    for category in get_categories(base_dir):
        file_path = os.path.join(base_dir, category, slug + ".md")
        if os.path.exists(file_path):
            return category
    return None


# ── Post Fonksiyonları ──────────────────────────────────────

def get_post_names():
    """Tüm kategorilerdeki postları listeler."""
    posts = []
    for category in get_categories(POSTS_DIR):
        cat_dir = os.path.join(POSTS_DIR, category)
        keywords = get_category_keywords(POSTS_DIR, category)
        for f in os.listdir(cat_dir):
            if not f.endswith(".md"):
                continue
            slug = os.path.splitext(f)[0]
            file_path = os.path.join(cat_dir, f)
            posts.append({
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "category": category,
                "keywords": keywords,
                "mtime": os.path.getmtime(file_path),
            })
    posts.sort(key=lambda x: x["mtime"], reverse=True)
    for p in posts:
        p["date"] = datetime.fromtimestamp(p["mtime"]).strftime("%d %B %Y %H:%M")
    return posts


def get_post_content(index=None):
    posts = get_post_names()
    if not posts:
        return "Any Posts Here", 404
    if index is None:
        index = numpy.random.randint(0, len(posts))
    post = posts[index]
    file_path = os.path.join(POSTS_DIR, post["category"], post["slug"] + ".md")

    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks","tables"])
    return {
        "name": post["slug"],
        "category": post["category"],
        "date": post["date"],
        "example_content": html_content,
    }


# ── Project Fonksiyonları ──────────────────────────────────────

def get_project_names():
    """Tüm kategorilerdeki projeleri listeler."""
    projects = []
    for category in get_categories(PROJECTS_DIR):
        cat_dir = os.path.join(PROJECTS_DIR, category)
        keywords = get_category_keywords(PROJECTS_DIR, category)
        for f in os.listdir(cat_dir):
            if not f.endswith(".md"):
                continue
            slug = os.path.splitext(f)[0]
            file_path = os.path.join(cat_dir, f)
            projects.append({
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "category": category,
                "keywords": keywords,
                "mtime": os.path.getmtime(file_path),
            })
    projects.sort(key=lambda x: x["mtime"], reverse=True)
    for p in projects:
        p["date"] = datetime.fromtimestamp(p["mtime"]).strftime("%d %B %Y %H:%M")
    return projects


def get_project_content(index=None):
    projects = get_project_names()
    if not projects:
        return "Any Projects Here", 404
    if index is None:
        index = numpy.random.randint(0, len(projects))
    project = projects[index]
    file_path = os.path.join(PROJECTS_DIR, project["category"], project["slug"] + ".md")

    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks","tables"])
    return {
        "name": project["slug"],
        "category": project["category"],
        "date": project["date"],
        "example_content": html_content,
    }

# ── Note Fonksiyonları ──────────────────────────────────────

def get_note_names():
    """Tüm kategorilerdeki notları listeler."""
    notes = []
    for category in get_categories(NOTES_DIR):
        cat_dir = os.path.join(NOTES_DIR, category)
        keywords = get_category_keywords(NOTES_DIR, category)
        for f in os.listdir(cat_dir):
            if not f.endswith(".md"):
                continue
            slug = os.path.splitext(f)[0]
            file_path = os.path.join(cat_dir, f)
            notes.append({
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "category": category,
                "keywords": keywords,
                "mtime": os.path.getmtime(file_path),
            })
    notes.sort(key=lambda x: x["mtime"], reverse=True)
    for p in notes:
        p["date"] = datetime.fromtimestamp(p["mtime"]).strftime("%d %B %Y %H:%M")
    return notes


def get_note_content(index=None):
    notes = get_note_names()
    if not notes:
        return "Any Notes Here", 404
    if index is None:
        index = numpy.random.randint(0, len(notes))
    note = notes[index]
    file_path = os.path.join(NOTES_DIR, note["category"], note["slug"] + ".md")

    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks","tables"])
    return {
        "name": note["slug"],
        "category": note["category"],
        "date": note["date"],
        "example_content": html_content,
    }


# ── Sayfalar ──────────────────────────────────────

@app.route("/")
def base_page():
    example_project = get_project_content()
    example_post = get_post_content()
    example_note = get_note_content()
    return render_template('main.html', example_post=example_post, example_project=example_project, example_note=example_note)


@app.route("/about")
def about_page():
    notes = get_note_names()
    projects = get_project_names()
    return render_template('about.html', notes=notes, projects=projects)


# ── Posts ──────────────────────────────────────

@app.route("/posts", methods=["GET", "POST"])
def posts_page():
    posts = get_post_names()
    example_content = get_post_content(0)
    return render_template("posts.html", posts=posts, example_content=example_content)


@app.route("/posts/<category>/<post_id>")
def show_post(category, post_id):
    post_file = os.path.join(POSTS_DIR, category, post_id + ".md")
    if not os.path.exists(post_file):
        return "Yazı bulunamadı", 404

    with open(post_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    stat = os.stat(post_file)
    ts = stat.st_ctime if platform.system() == "Windows" else stat.st_mtime
    created_time = datetime.fromtimestamp(ts).strftime("%Y %m %d")

    keywords = get_category_keywords(POSTS_DIR, category)
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables"])

    return render_template('post.html',
        content=html_content,
        post_id=post_id,
        category=category,
        keywords=keywords,
        created_time=created_time,
    )


@app.route("/posts/add", methods=["GET", "POST"])
def add_post():
    if request.method == "POST":
        psw = request.form.get("psw")
        title = request.form.get("title")
        file = request.files.get("file")
        category_select = request.form.get("category_select")
        new_category = request.form.get("new_category")
        new_keywords = request.form.get("new_keywords")

        # Şifre kontrolü
        if not psw:
            return "Key girilmedi", 400
        if not bcrypt.checkpw(psw.encode(), HASHED_PSW):
            return "Key yanlış", 403

        # Başlık kontrolleri
        if not title:
            return "Başlık boş olamaz", 400
        if title == "add":
            return "Başlık 'add' olamaz", 400

        # Dosya kontrolleri
        if not file or file.filename == "":
            return "Dosya seçilmedi", 400
        if not allowed_file(file.filename):
            return "Sadece .md dosyası kabul edilir", 400

        # Kategori belirleme
        if category_select == "__new__" and new_category:
            category = slugify(new_category)
            keywords_text = new_keywords.strip() if new_keywords else "#" + category
            ensure_category_dir(POSTS_DIR, category, keywords_text)
        elif category_select:
            category = category_select
        else:
            return "Kategori seçilmedi", 400

        # Slug oluşturma
        slug = slugify(title)
        base_slug = slug
        i = 1
        cat_dir = os.path.join(POSTS_DIR, category)
        while os.path.exists(os.path.join(cat_dir, slug + ".md")):
            slug = f"{base_slug}-{i}"
            i += 1

        save_path = os.path.join(cat_dir, slug + ".md")
        file.save(save_path)
        return redirect(url_for("posts_page"))

    categories = get_categories(POSTS_DIR)
    return render_template("add_post.html", categories=categories)


@app.route("/posts/download/<category>/<post_id>")
def download_post(category, post_id):
    directory = os.path.join("posts", category)
    return send_from_directory(
        directory=directory,
        path=f"{post_id}.md",
        as_attachment=True,
    )


@app.route("/posts/update/<category>/<post_id>", methods=["GET", "POST"])
def update_post(category, post_id):
    post_path = os.path.join(POSTS_DIR, category, f"{post_id}.md")

    if request.method == "GET":
        if not os.path.exists(post_path):
            abort(404)
        with open(post_path, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template("update_post.html", post_id=post_id, category=category, content=content)

    key = request.form.get("key")
    action = request.form.get("action")

    if not key:
        abort(400)
    if not bcrypt.checkpw(key.encode("utf-8"), HASHED_PSW):
        return "Key yanlış", 403

    post_path = os.path.join(POSTS_DIR, category, f"{post_id}.md")

    # Save (New action)
    if action == "save":
        content = request.form.get("content")
        if content is None:
            abort(400)
        # Dosya içeriğini güncelle (overwrite)
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Kaydettikten sonra postu görüntülemeye git (veya tekrar edit sayfasına)
        return redirect(url_for("show_post", category=category, post_id=post_id))

    # Upload (Eski yöntem, isterseniz kaldırabilirsiniz veya alternatif olarak tutabilirsiniz)
    if action == "upload":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".md"):
            abort(400)
        file.save(post_path)
        return redirect(url_for("posts_page"))

    # Delete
    if action == "delete":
        confirm_slug = request.form.get("confirm_slug")
        if confirm_slug != post_id:
            return "Slug eşleşmiyor", 403
        if not os.path.exists(post_path):
            abort(404)
        os.remove(post_path)
        return redirect(url_for("posts_page"))

    abort(400)


# ── Projects ──────────────────────────────────────

@app.route("/projects")
def projects_page():
    projects = get_project_names()
    example_content = get_project_content(0)
    return render_template("projects.html", projects=projects, example_content=example_content)


@app.route("/projects/<category>/<project_id>")
def show_project(category, project_id):
    project_file = os.path.join(PROJECTS_DIR, category, project_id + ".md")
    if not os.path.exists(project_file):
        return "Yazı bulunamadı", 404

    with open(project_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    stat = os.stat(project_file)
    ts = stat.st_ctime if platform.system() == "Windows" else stat.st_mtime
    created_time = datetime.fromtimestamp(ts).strftime("%Y %m %d")

    keywords = get_category_keywords(PROJECTS_DIR, category)
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables"])

    return render_template('project.html',
        content=html_content,
        project_id=project_id,
        category=category,
        keywords=keywords,
        created_time=created_time,
    )


@app.route("/projects/add", methods=["GET", "POST"])
def add_project():
    if request.method == "POST":
        psw = request.form.get("psw")
        title = request.form.get("title")
        file = request.files.get("file")
        category_select = request.form.get("category_select")
        new_category = request.form.get("new_category")
        new_keywords = request.form.get("new_keywords")

        # Şifre kontrolü
        if not psw:
            return "Key girilmedi", 400
        if not bcrypt.checkpw(psw.encode(), HASHED_PSW):
            return "Key yanlış", 403

        if not title:
            return "Başlık boş olamaz", 400
        if title == "add":
            return "Başlık 'add' olamaz", 400

        if not file or file.filename == "":
            return "Dosya seçilmedi", 400
        if not allowed_file(file.filename):
            return "Sadece .md dosyası kabul edilir", 400

        # Kategori belirleme
        if category_select == "__new__" and new_category:
            category = slugify(new_category)
            keywords_text = new_keywords.strip() if new_keywords else "#" + category
            ensure_category_dir(PROJECTS_DIR, category, keywords_text)
        elif category_select:
            category = category_select
        else:
            return "Kategori seçilmedi", 400

        # Slug oluşturma
        slug = slugify(title)
        base_slug = slug
        i = 1
        cat_dir = os.path.join(PROJECTS_DIR, category)
        while os.path.exists(os.path.join(cat_dir, slug + ".md")):
            slug = f"{base_slug}-{i}"
            i += 1

        save_path = os.path.join(cat_dir, slug + ".md")
        file.save(save_path)
        return redirect(url_for("projects_page"))

    categories = get_categories(PROJECTS_DIR)
    return render_template("add_project.html", categories=categories)


@app.route("/projects/download/<category>/<project_id>")
def download_project(category, project_id):
    directory = os.path.join("projects", category)
    return send_from_directory(
        directory=directory,
        path=f"{project_id}.md",
        as_attachment=True,
    )


@app.route("/projects/update/<category>/<project_id>", methods=["GET", "POST"])
def update_project(category, project_id):
    project_path = os.path.join(PROJECTS_DIR, category, f"{project_id}.md")

    if request.method == "GET":
        if not os.path.exists(project_path):
            abort(404)
        with open(project_path, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template("update_project.html", project_id=project_id, category=category, content=content)

    key = request.form.get("key")
    action = request.form.get("action")

    if not key or not action:
        abort(400)
    if not bcrypt.checkpw(key.encode("utf-8"), HASHED_PSW):
        return "Key yanlış", 403

    project_path = os.path.join(PROJECTS_DIR, category, f"{project_id}.md")

    # Save (New action)
    if action == "save":
        content = request.form.get("content")
        if content is None:
            abort(400)
        with open(project_path, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("show_project", category=category, project_id=project_id))

    # Upload
    if action == "upload":
        file = request.files.get("file")
        if not file or file.filename == "":
            abort(400)
        if not file.filename.endswith(".md"):
            abort(400)
        file.save(project_path)
        return redirect(url_for("show_project", category=category, project_id=project_id))

    # Delete
    if action == "delete":
        confirm_slug = request.form.get("confirm_slug")
        if not confirm_slug:
            abort(400)
        if confirm_slug != project_id:
            return "Slug eşleşmiyor", 403
        if not os.path.exists(project_path):
            abort(404)
        os.remove(project_path)
        return redirect(url_for("projects_page"))

    abort(400)


# ── Notes ──────────────────────────────────────

@app.route("/notes")
def notes_page():
    notes = get_note_names()
    example_content = get_note_content(0)
    return render_template("notes.html", notes=notes, example_content=example_content)


@app.route("/notes/<category>/<note_id>")
def show_note(category, note_id):
    note_file = os.path.join(NOTES_DIR, category, note_id + ".md")
    if not os.path.exists(note_file):
        return "Not bulunamadı", 404

    with open(note_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    stat = os.stat(note_file)
    ts = stat.st_ctime if platform.system() == "Windows" else stat.st_mtime
    created_time = datetime.fromtimestamp(ts).strftime("%Y %m %d")

    keywords = get_category_keywords(NOTES_DIR, category)
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables"])

    return render_template('note.html',
        content=html_content,
        note_id=note_id,
        category=category,
        keywords=keywords,
        created_time=created_time,
    )


@app.route("/notes/add", methods=["GET", "POST"])
def add_note():
    if request.method == "POST":
        psw = request.form.get("psw")
        title = request.form.get("title")
        file = request.files.get("file")
        category_select = request.form.get("category_select")
        new_category = request.form.get("new_category")
        new_keywords = request.form.get("new_keywords")

        # Şifre kontrolü
        if not psw:
            return "Key girilmedi", 400
        if not bcrypt.checkpw(psw.encode(), HASHED_PSW):
            return "Key yanlış", 403

        if not title:
            return "Başlık boş olamaz", 400
        if title == "add":
            return "Başlık 'add' olamaz", 400

        if not file or file.filename == "":
            return "Dosya seçilmedi", 400
        if not allowed_file(file.filename):
            return "Sadece .md dosyası kabul edilir", 400

        # Kategori belirleme
        if category_select == "__new__" and new_category:
            category = slugify(new_category)
            keywords_text = new_keywords.strip() if new_keywords else "#" + category
            ensure_category_dir(NOTES_DIR, category, keywords_text)
        elif category_select:
            category = category_select
        else:
            return "Kategori seçilmedi", 400

        # Slug oluşturma
        slug = slugify(title)
        base_slug = slug
        i = 1
        cat_dir = os.path.join(NOTES_DIR, category)
        while os.path.exists(os.path.join(cat_dir, slug + ".md")):
            slug = f"{base_slug}-{i}"
            i += 1

        save_path = os.path.join(cat_dir, slug + ".md")
        file.save(save_path)
        return redirect(url_for("notes_page"))

    categories = get_categories(NOTES_DIR)
    return render_template("add_note.html", categories=categories)


@app.route("/notes/download/<category>/<note_id>")
def download_note(category, note_id):
    directory = os.path.join("notes", category)
    return send_from_directory(
        directory=directory,
        path=f"{note_id}.md",
        as_attachment=True,
    )


@app.route("/notes/update/<category>/<note_id>", methods=["GET", "POST"])
def update_note(category, note_id):
    note_path = os.path.join(NOTES_DIR, category, f"{note_id}.md")

    if request.method == "GET":
        if not os.path.exists(note_path):
            abort(404)
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template("update_note.html", note_id=note_id, category=category, content=content)

    key = request.form.get("key")
    action = request.form.get("action")

    if not key or not action:
        abort(400)
    if not bcrypt.checkpw(key.encode("utf-8"), HASHED_PSW):
        return "Key yanlış", 403

    note_path = os.path.join(NOTES_DIR, category, f"{note_id}.md")

    # Save
    if action == "save":
        content = request.form.get("content")
        if content is None:
            abort(400)
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("show_note", category=category, note_id=note_id))

    # Upload
    if action == "upload":
        file = request.files.get("file")
        if not file or file.filename == "":
            abort(400)
        if not file.filename.endswith(".md"):
            abort(400)
        file.save(note_path)
        return redirect(url_for("show_note", category=category, note_id=note_id))

    # Delete
    if action == "delete":
        confirm_slug = request.form.get("confirm_slug")
        if not confirm_slug:
            abort(400)
        if confirm_slug != note_id:
            return "Slug eşleşmiyor", 403
        if not os.path.exists(note_path):
            abort(404)
        os.remove(note_path)
        return redirect(url_for("notes_page"))

    abort(400)


if __name__ == "__main__":
    app.run(debug=True)