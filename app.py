import os
import hmac

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)


# =========================================================
# CONFIGURAÇÃO
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    ""
)


# =========================================================
# ADMINISTRADOR
# =========================================================

ADMIN_USUARIO = os.environ.get(
    "ADMIN_USUARIO",
    ""
)

ADMIN_SENHA = os.environ.get(
    "ADMIN_SENHA",
    ""
)


# =========================================================
# PASTA DE ARQUIVOS
# =========================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

ARQUIVOS_DIR = os.path.join(
    BASE_DIR,
    "arquivos"
)

os.makedirs(
    ARQUIVOS_DIR,
    exist_ok=True
)


# =========================================================
# FUNÇÕES DE SEGURANÇA
# =========================================================

def usuario_logado():
    return "usuario" in session


def usuario_admin():
    return session.get(
        "admin",
        False
    )


def arquivo_e_py(nome):
    return nome.lower().endswith(
        ".py"
    )


def app_py_protegido(nome):
    return os.path.basename(
        nome
    ).lower() == "app.py"


def caminho_seguro(nome):

    nome = os.path.normpath(
        nome
    )

    if nome.startswith(".."):
        return None

    if os.path.isabs(nome):
        return None

    caminho = os.path.abspath(
        os.path.join(
            ARQUIVOS_DIR,
            nome
        )
    )

    if os.path.commonpath(
        [ARQUIVOS_DIR, caminho]
    ) != ARQUIVOS_DIR:
        return None

    return caminho


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
def index():

    if usuario_logado():
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        # -------------------------------------------------
        # COMPARAÇÃO SEGURA
        # -------------------------------------------------

        usuario_correto = hmac.compare_digest(
            usuario,
            ADMIN_USUARIO
        )

        senha_correta = hmac.compare_digest(
            senha,
            ADMIN_SENHA
        )

        # -------------------------------------------------
        # LOGIN CORRETO
        # -------------------------------------------------

        if (
            usuario_correto
            and senha_correta
        ):

            session.clear()

            session["usuario"] = usuario
            session["admin"] = True

            return redirect(
                url_for("dashboard")
            )

        # -------------------------------------------------
        # LOGIN INCORRETO
        # -------------------------------------------------

        flash(
            "Usuário ou senha incorretos.",
            "erro"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    return render_template(
        "dashboard.html",
        usuario=session.get(
            "usuario"
        ),
        admin=usuario_admin()
    )


# =========================================================
# DADOS DO USUÁRIO
# =========================================================

@app.route(
    "/dados-usuario",
    methods=["GET", "POST"]
)
def dados_usuario():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        flash(
            "Dados guardados com sucesso.",
            "sucesso"
        )

        return redirect(
            url_for("dados_usuario")
        )

    return render_template(
        "dados-usuario.html"
    )


# =========================================================
# LISTAR ARQUIVOS
# =========================================================

@app.route("/arquivos")
def arquivos():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    lista = []

    for raiz, diretorios, ficheiros in os.walk(
        ARQUIVOS_DIR
    ):

        for ficheiro in ficheiros:

            caminho_completo = os.path.join(
                raiz,
                ficheiro
            )

            relativo = os.path.relpath(
                caminho_completo,
                ARQUIVOS_DIR
            )

            lista.append(
                relativo
            )

    lista.sort()

    return render_template(
        "arquivos.html",
        arquivos=lista,
        admin=usuario_admin()
    )


# =========================================================
# VISUALIZAR ARQUIVO
# =========================================================

@app.route(
    "/visualizar/<path:nome>"
)
def visualizar(nome):

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    caminho = caminho_seguro(
        nome
    )

    if (
        caminho is None
        or not os.path.isfile(caminho)
    ):

        flash(
            "Ficheiro não encontrado.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    # -------------------------------------------------
    # ARQUIVOS PY
    # -------------------------------------------------

    if arquivo_e_py(nome):

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as f:

                conteudo = f.read()

        except (
            UnicodeDecodeError,
            OSError
        ):

            flash(
                "Não foi possível ler este ficheiro.",
                "erro"
            )

            return redirect(
                url_for("arquivos")
            )

        return render_template(
            "editor.html",
            nome=nome,
            conteudo=conteudo,
            admin=usuario_admin(),
            somente_visualizacao=not usuario_admin()
        )

    # -------------------------------------------------
    # OUTROS ARQUIVOS
    # -------------------------------------------------

    return send_from_directory(
        ARQUIVOS_DIR,
        nome
    )


# =========================================================
# EDITAR ARQUIVO PY
# SOMENTE ADMINISTRADOR
# =========================================================

@app.route(
    "/editar/<path:nome>",
    methods=["POST"]
)
def editar(nome):

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    if not usuario_admin():

        flash(
            "Apenas o administrador pode editar ficheiros.",
            "erro"
        )

        return redirect(
            url_for(
                "visualizar",
                nome=nome
            )
        )

    if not arquivo_e_py(nome):

        flash(
            "Somente ficheiros .py podem ser editados.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    # -------------------------------------------------
    # APP.PY PROTEGIDO
    # -------------------------------------------------

    if app_py_protegido(nome):

        flash(
            "O ficheiro app.py está protegido.",
            "erro"
        )

        return redirect(
            url_for(
                "visualizar",
                nome=nome
            )
        )

    caminho = caminho_seguro(
        nome
    )

    if (
        caminho is None
        or not os.path.isfile(caminho)
    ):

        flash(
            "Ficheiro não encontrado.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    conteudo = request.form.get(
        "conteudo",
        ""
    )

    try:

        with open(
            caminho,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                conteudo
            )

        flash(
            "Ficheiro guardado com sucesso.",
            "sucesso"
        )

    except OSError as e:

        flash(
            f"Erro ao guardar: {e}",
            "erro"
        )

    return redirect(
        url_for(
            "visualizar",
            nome=nome
        )
    )


# =========================================================
# CRIAR ARQUIVO PY
# SOMENTE ADMINISTRADOR
# =========================================================

@app.route(
    "/novo-arquivo",
    methods=["GET", "POST"]
)
def novo_arquivo():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    if not usuario_admin():

        flash(
            "Apenas o administrador pode criar ficheiros.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        if not nome:

            flash(
                "Digite o nome do ficheiro.",
                "erro"
            )

            return redirect(
                url_for("novo_arquivo")
            )

        if not arquivo_e_py(nome):

            flash(
                "O ficheiro deve ter extensão .py.",
                "erro"
            )

            return redirect(
                url_for("novo_arquivo")
            )

        if app_py_protegido(nome):

            flash(
                "Não é permitido criar ou substituir app.py.",
                "erro"
            )

            return redirect(
                url_for("novo_arquivo")
            )

        caminho = caminho_seguro(
            nome
        )

        if caminho is None:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("novo_arquivo")
            )

        if os.path.exists(caminho):

            flash(
                "Esse ficheiro já existe.",
                "erro"
            )

            return redirect(
                url_for("novo_arquivo")
            )

        try:

            os.makedirs(
                os.path.dirname(caminho),
                exist_ok=True
            )

            with open(
                caminho,
                "w",
                encoding="utf-8"
            ) as f:

                f.write("")

            flash(
                "Ficheiro criado com sucesso.",
                "sucesso"
            )

            return redirect(
                url_for(
                    "visualizar",
                    nome=nome
                )
            )

        except OSError as e:

            flash(
                f"Erro ao criar ficheiro: {e}",
                "erro"
            )

    return render_template(
        "novo-arquivo.html"
    )


# =========================================================
# UPLOAD DE ARQUIVO PY
# SOMENTE ADMINISTRADOR
# =========================================================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload():

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    if not usuario_admin():

        flash(
            "Apenas o administrador pode fazer upload.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    if request.method == "POST":

        ficheiro = request.files.get(
            "arquivo"
        )

        # -------------------------------------------------
        # VERIFICAR ARQUIVO
        # -------------------------------------------------

        if ficheiro is None:

            flash(
                "Nenhum ficheiro selecionado.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # -------------------------------------------------
        # PEGAR NOME ORIGINAL
        # -------------------------------------------------

        nome_original = ficheiro.filename

        if not nome_original:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # -------------------------------------------------
        # PEGAR SOMENTE O NOME
        # -------------------------------------------------

        nome = os.path.basename(
            nome_original
        )

        # -------------------------------------------------
        # SOMENTE .PY
        # -------------------------------------------------

        if not nome.lower().endswith(
            ".py"
        ):

            flash(
                "Somente ficheiros .py podem ser enviados.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # -------------------------------------------------
        # PROTEGER APP.PY
        # -------------------------------------------------

        if nome.lower() == "app.py":

            flash(
                "O ficheiro app.py está protegido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # -------------------------------------------------
        # CAMINHO SEGURO
        # -------------------------------------------------

        caminho = caminho_seguro(
            nome
        )

        if caminho is None:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # -------------------------------------------------
        # SALVAR
        # -------------------------------------------------

        try:

            ficheiro.save(
                caminho
            )

            flash(
                "Ficheiro enviado com sucesso.",
                "sucesso"
            )

        except OSError as e:

            flash(
                f"Erro no upload: {e}",
                "erro"
            )

    return render_template(
        "upload.html"
    )


# =========================================================
# EXCLUIR ARQUIVO PY
# SOMENTE ADMINISTRADOR
# =========================================================

@app.route(
    "/excluir/<path:nome>",
    methods=["POST"]
)
def excluir(nome):

    if not usuario_logado():

        return redirect(
            url_for("login")
        )

    if not usuario_admin():

        flash(
            "Apenas o administrador pode excluir ficheiros.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    if not arquivo_e_py(nome):

        flash(
            "Somente ficheiros .py podem ser excluídos.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    if app_py_protegido(nome):

        flash(
            "O ficheiro app.py não pode ser excluído.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    caminho = caminho_seguro(
        nome
    )

    if (
        caminho is None
        or not os.path.isfile(caminho)
    ):

        flash(
            "Ficheiro não encontrado.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    try:

        os.remove(
            caminho
        )

        flash(
            "Ficheiro excluído com sucesso.",
            "sucesso"
        )

    except OSError as e:

        flash(
            f"Erro ao excluir: {e}",
            "erro"
        )

    return redirect(
        url_for("arquivos")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# EXECUTAR APLICAÇÃO
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )