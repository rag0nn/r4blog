from flask import Flask, render_template, request, redirect, url_for, send_from_directory,abort

import markdown2
import os
from slugify import slugify
from datetime import datetime
import numpy
import bcrypt

app = Flask(__name__, template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, "posts")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {"md"}
HASHED_PSW = b"$2b$12$qz7nWTqfIdbrsw6MDZ10Ce/p7nspqKfZYu52CCiLlQ5ZNevXWEEhe"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS and filename

def get_post_names():
    posts = [
        {
            "slug": os.path.splitext(f)[0],
            "title": os.path.splitext(f)[0].replace("-", " ").title(),
            "mtime": os.path.getmtime(os.path.join(POSTS_DIR, f))
        }
        for f in os.listdir(POSTS_DIR)
        if f.endswith(".md")
    ]
    posts.sort(key=lambda x: x["mtime"], reverse=True)
    # timestamp → readable date
    for p in posts:
        p["date"] = datetime.fromtimestamp(p["mtime"]).strftime("%d %B %Y %H:%M")
    return posts
    
def get_post_content(index:int=None):
    posts = get_post_names()
    if not posts:
        return "Any Posts Here",404
    if index is None:
        index = numpy.random.randint(0,len(posts))
    name = f"{POSTS_DIR}/{posts[index]['slug']}.md"
    
    with open(name, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks"])
    content = {
        "name" : posts[index]['slug'],
        "date" : posts[index]['date'],
        "example_content": html_content
    }
    return content
    
def get_project_names():
    projects = [
        {
            "slug": os.path.splitext(f)[0],
            "title": os.path.splitext(f)[0].replace("-", " ").title(),
            "mtime": os.path.getmtime(os.path.join(PROJECTS_DIR, f))
        }
        for f in os.listdir(PROJECTS_DIR)
        if f.endswith(".md")
    ]
    projects.sort(key=lambda x: x["mtime"], reverse=True)
    # timestamp → readable date
    for p in projects:
        p["date"] = datetime.fromtimestamp(p["mtime"]).strftime("%d %B %Y %H:%M")
    
    return projects

def get_project_content(index:int = None):
    projects = get_project_names()
    if not projects:
        return "Any Projects Here",404
    if index is None:
        index = numpy.random.randint(0,len(projects))

    name = f"{PROJECTS_DIR}/{projects[index]['slug']}.md"
    with open(name, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks"])
    content = {
        "name" : projects[index]['slug'],
        "date" : projects[index]['date'],
        "example_content": html_content
    }
    return content

@app.route("/")
def base_page():
    example_project = get_project_content()
    example_post = get_post_content()
    return render_template('main.html', example_post=example_post, example_project=example_project)

@app.route("/about")
def about_page():
    posts = get_post_names()
    projects = get_project_names()
    return render_template('about.html', posts=posts, projects=projects)

@app.route("/posts", methods=["GET", "POST"])
def posts_page():
    posts = get_post_names()
    example_content = get_post_content(0)
    return render_template("posts.html", posts=posts, example_content=example_content)

@app.route("/posts/<post_id>")
def show_post(post_id):
    post_file = f"{POSTS_DIR}/{post_id}.md"
    if not os.path.exists(post_file):
        return "Yazı bulunamadı", 404
    
    with open(post_file, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks"])
    variables = {
        "content" : html_content,
        "post_id" : post_id
    }
    
    return render_template('post.html', **variables)

@app.route("/posts/add", methods=["GET", "POST"])
def add_post():
    if request.method == "POST":
        psw   = request.form.get("psw")
        title = request.form.get("title")
        file  = request.files.get("file")

        # ŞİFRE KONTROLÜ
        if not psw:
            return "Key girilmedi", 400

        if not bcrypt.checkpw(psw.encode(), HASHED_PSW):
            return "Key yanlış", 403

        # BAŞLIK KONTROLLERİ
        if not title:
            return "Başlık boş olamaz", 400
        
        if title == "add":
            return "Başlık 'add' olamaz", 400

        # DOSYA KONTROLLERİ
        if not file or file.filename == "":
            return "Dosya seçilmedi", 400

        if not allowed_file(file.filename):
            return "Sadece .md dosyası kabul edilir", 400

        # 🔗 SLUG OLUŞTURMA
        slug = slugify(title)
        base_slug = slug
        i = 1
        while os.path.exists(os.path.join(POSTS_DIR, slug + ".md")):
            slug = f"{base_slug}-{i}"
            i += 1

        filename = slug + ".md"
        save_path = os.path.join(POSTS_DIR, filename)

        file.save(save_path)

        return redirect(url_for("posts_page"))

    return render_template("add_post.html")

@app.route("/posts/download/<post_id>")
def download_post(post_id):
    return send_from_directory(
        directory="posts",      # md dosyalarının olduğu klasör
        path=f"{post_id}.md",
        as_attachment=True
    )

@app.route("/posts/update/<post_id>", methods=["GET", "POST"])
def update_post(post_id):

    # SAYFAYI GÖSTER
    if request.method == "GET":
        return render_template("update_post.html", post_id=post_id)

    # UPLOAD İŞLEMİ
    key = request.form.get("key")
    file = request.files.get("file")

    if not key or not file:
        abort(400)

    if not bcrypt.checkpw(key.encode(), HASHED_PSW):
        return "Key yanlış", 403

    if not file.filename.endswith(".md"):
        abort(400)

    save_path = os.path.join(POSTS_DIR, f"{post_id}.md")
    file.save(save_path)

    return redirect(url_for("show_post", post_id=post_id))

@app.route("/projects/download/<project_id>")
def download_project(project_id):
    return send_from_directory(
        directory="projects",      # md dosyalarının olduğu klasör
        path=f"{project_id}.md",
        as_attachment=True
    )

@app.route("/projects/update/<project_id>", methods=["GET", "POST"])
def update_project(project_id):

    # SAYFAYI GÖSTER
    if request.method == "GET":
        return render_template("update_project.html", project_id=project_id)

    # UPLOAD İŞLEMİ
    key = request.form.get("key")
    file = request.files.get("file")

    if not key or not file:
        abort(400)

    if not bcrypt.checkpw(key.encode(), HASHED_PSW):
        return "Key yanlış", 403

    if not file.filename.endswith(".md"):
        abort(400)

    save_path = os.path.join(PROJECTS_DIR, f"{project_id}.md")
    file.save(save_path)

    return redirect(url_for("show_project", project_id=project_id))

@app.route("/projects")
def projects_page():
    projects = get_project_names()
    example_content = get_project_content(0)
    return render_template("projects.html", projects=projects, example_content=example_content)

@app.route("/projects/<project_id>")
def show_project(project_id):
    post_file = f"{PROJECTS_DIR}/{project_id}.md"
    if not os.path.exists(post_file):
        return "Yazı bulunamadı", 404
    
    with open(post_file, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks"])
    variables = {
        "content" : html_content,
        "project_id" : project_id
    }
    
    return render_template('project.html', **variables)

@app.route("/projects/add", methods=["GET", "POST"])
def add_project():
    if request.method == "POST":
        psw   = request.form.get("psw")
        title = request.form.get("title")
        file = request.files.get("file")

        # ŞİFRE KONTROLÜ
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

        slug = slugify(title)

        # slug çakışmasını önle
        base_slug = slug
        i = 1
        while os.path.exists(os.path.join(PROJECTS_DIR, slug + ".md")):
            slug = f"{base_slug}-{i}"
            i += 1

        filename = slug + ".md"
        save_path = os.path.join(PROJECTS_DIR, filename)

        file.save(save_path)

        return redirect(url_for("projects_page"))

    return render_template("add_project.html")

if __name__ == "__main__":
    app.run(debug=True)