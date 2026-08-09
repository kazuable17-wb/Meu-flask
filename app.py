from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)

app.secret_key = "minha_chave_secreta"


# =========================
# INÍCIO
# =========================

@app.route("/")
def inicio():
    return redirect(url_for("login"))


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == "admin" and senha == "1234":

            session["usuario"] = usuario

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            erro="Usuário ou senha incorretos"
        )

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        usuario=session["usuario"]
    )


# =========================
# DADOS DO USUÁRIO
# =========================

@app.route("/dados-usuario", methods=["GET", "POST"])
def dados_usuario():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        nome = request.form.get("nome")
        idade = request.form.get("idade")
        sexo = request.form.get("sexo")
        telefone = request.form.get("telefone")
        email = request.form.get("email")

        session["dados_usuario"] = {
            "nome": nome,
            "idade": idade,
            "sexo": sexo,
            "telefone": telefone,
            "email": email
        }

        return redirect(url_for("dashboard"))

    return render_template("dados_usuario.html")


# =========================
# FICHEIROS
# =========================

@app.route("/ficheiros")
def ficheiros():

    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("python_files.html")


# =========================
# PYTHON FILES
# =========================

@app.route("/python-files")
def python_files():

    if "usuario" not in session:
        return redirect(url_for("login"))

    pasta = os.path.dirname(os.path.abspath(__file__))

    arquivos = [
        arquivo
        for arquivo in os.listdir(pasta)
        if arquivo.endswith(".py")
    ]

    return render_template(
        "python_files.html",
        arquivos=arquivos
    )


# =========================
# EXCLUIR ARQUIVO
# =========================

@app.route("/excluir-arquivo/<nome>")
def excluir_arquivo(nome):

    if "usuario" not in session:
        return redirect(url_for("login"))

    # Não permitir apagar o próprio sistema
    if nome == "app.py":
        return "O app.py não pode ser excluído.", 403

    if not nome.endswith(".py"):
        return "Arquivo não permitido.", 403

    nome = os.path.basename(nome)

    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, nome)

    if os.path.isfile(caminho):
        os.remove(caminho)

    return redirect(url_for("python_files"))


# =========================
# NOVO ARQUIVO
# =========================

@app.route("/novo-arquivo", methods=["GET", "POST"])
def novo_arquivo():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        nome = request.form.get("nome", "").strip()

        if not nome:
            return "Nome inválido", 400

        if not nome.endswith(".py"):
            nome += ".py"

        # Evitar nomes perigosos
        nome = os.path.basename(nome)

        pasta = os.path.dirname(os.path.abspath(__file__))
        caminho = os.path.join(pasta, nome)

        if os.path.exists(caminho):
            return "Esse ficheiro já existe.", 400

        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write("# Novo ficheiro Python\n\n")

        return redirect(
            url_for("ver_arquivo", nome=nome)
        )

    return """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <title>Novo ficheiro</title>

    <style>
        body {
            background: #1e1e1e;
            color: white;
            font-family: Arial;
            padding: 40px;
        }

        input {
            padding: 12px;
            width: 300px;
            background: #252526;
            color: white;
            border: 1px solid #555;
        }

        button {
            padding: 12px 20px;
            background: #007acc;
            color: white;
            border: none;
            cursor: pointer;
        }
    </style>
</head>

<body>

    <h1>🐍 Novo ficheiro Python</h1>

    <form method="POST">

        <input
            type="text"
            name="nome"
            placeholder="exemplo.py"
            required
        >

        <button type="submit">
            Criar
        </button>

    </form>

</body>
</html>
"""


# =========================
# VER / EDITAR ARQUIVO
# =========================

@app.route("/ver-arquivo/<nome>", methods=["GET", "POST"])
def ver_arquivo(nome):

    if "usuario" not in session:
        return redirect(url_for("login"))

    if not nome.endswith(".py"):
        return "Arquivo não permitido", 403

    nome = os.path.basename(nome)

    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, nome)

    if not os.path.isfile(caminho):
        return "Arquivo não encontrado", 404

    if request.method == "POST":

        codigo = request.form.get("codigo", "")

        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(codigo)

        return redirect(
            url_for("ver_arquivo", nome=nome)
        )

    with open(caminho, "r", encoding="utf-8") as arquivo:
        codigo = arquivo.read()

    return render_template(
        "editar_arquivo.html",
        nome=nome,
        codigo=codigo
    )


# =========================
# UPLOAD
# =========================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        arquivo = request.files.get("arquivo")

        if arquivo and arquivo.filename:

            if arquivo.filename.endswith(".py"):

                nome = os.path.basename(arquivo.filename)

                pasta = os.path.dirname(os.path.abspath(__file__))
                caminho = os.path.join(pasta, nome)

                arquivo.save(caminho)

                return redirect(
                    url_for("python_files")
                )

            return "Apenas ficheiros .py são permitidos."

    return render_template("upload.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================
# INICIAR SERVIDOR
# =========================

if __name__ == "__main__":
    app.run(debug=True)