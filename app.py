
import os
import hmac
import mimetypes

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    abort,
)


# =========================================================
# CONFIGURAÇÃO
# =========================================================

app = Flask(__name__)


# =========================================================
# SEGURANÇA DA SESSÃO
# =========================================================

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY não configurada. "
        "Adicione SECRET_KEY nas Environment Variables do Render."
    )

app.config["SECRET_KEY"] = SECRET_KEY

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "true").lower() == "true"
)

# Limite máximo de upload: 16 MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# =========================================================
# UTILIZADORES
# =========================================================

ADMIN_USUARIO = os.environ.get("ADMIN_USUARIO", "")
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "")

USUARIO = os.environ.get("USUARIO", "")
USUARIO_SENHA = os.environ.get("USUARIO_SENHA", "")


if not ADMIN_USUARIO or not ADMIN_SENHA:
    raise RuntimeError(
        "ADMIN_USUARIO e ADMIN_SENHA devem ser configurados "
        "nas Environment Variables do Render."
    )


if not USUARIO or not USUARIO_SENHA:
    raise RuntimeError(
        "USUARIO e USUARIO_SENHA devem ser configurados "
        "nas Environment Variables do Render."
    )


# =========================================================
# PASTA DE ARQUIVOS
# =========================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

ARQUIVOS_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "arquivos")
)

os.makedirs(ARQUIVOS_DIR, exist_ok=True)


# =========================================================
# CABEÇALHOS DE SEGURANÇA
# =========================================================

@app.after_request
def adicionar_cabecalhos_seguranca(response):

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "script-src 'self' 'unsafe-inline' https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "media-src 'self' blob:; "
        "frame-src 'self' blob:; "
        "frame-ancestors 'self';"
    )

    return response


# =========================================================
# AUTENTICAÇÃO
# =========================================================

def usuario_logado():
    return bool(session.get("usuario"))


def usuario_admin():
    return session.get("admin") is True


def exigir_login():

    if not usuario_logado():
        return redirect(url_for("login"))

    return None


def exigir_admin():

    if not usuario_logado():
        return redirect(url_for("login"))

    if not usuario_admin():

        flash(
            "Acesso negado. Apenas o administrador pode executar esta operação.",
            "erro",
        )

        return redirect(url_for("dashboard"))

    return None


# =========================================================
# SEGURANÇA DE ARQUIVOS
# =========================================================

def arquivo_e_py(nome):
    return nome.lower().endswith(".py")


def app_py_protegido(nome):
    return os.path.basename(nome).lower() == "app.py"


def caminho_seguro(nome):
    """
    Converte um nome relativo para caminho absoluto
    dentro da pasta ARQUIVOS_DIR.

    Impede:
        ../
        ../../
        caminhos absolutos
        acesso fora da pasta arquivos/
    """

    if not nome:
        return None

    nome = str(nome).replace("\\", "/").strip()

    if not nome:
        return None

    # Impede caminho absoluto Linux
    if nome.startswith("/"):
        return None

    # Impede caminho absoluto Windows
    if len(nome) >= 2 and nome[1] == ":":
        return None

    caminho = os.path.abspath(
        os.path.join(
            ARQUIVOS_DIR,
            nome
        )
    )

    try:

        pasta_real = os.path.realpath(
            ARQUIVOS_DIR
        )

        caminho_real = os.path.realpath(
            caminho
        )

        if os.path.commonpath(
            [pasta_real, caminho_real]
        ) != pasta_real:

            return None

    except (ValueError, OSError):

        return None

    return caminho


def nome_arquivo_seguro(nome):
    """
    Retorna somente o nome do arquivo.
    """

    if not nome:
        return None

    nome = os.path.basename(
        nome
    ).strip()

    if not nome:
        return None

    if nome in (".", ".."):
        return None

    return nome


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

    if usuario_logado():
        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )

        # ADMIN

        admin_usuario_correto = hmac.compare_digest(
            usuario,
            ADMIN_USUARIO
        )

        admin_senha_correta = hmac.compare_digest(
            senha,
            ADMIN_SENHA
        )

        if (
            admin_usuario_correto
            and admin_senha_correta
        ):

            session.clear()

            session["usuario"] = ADMIN_USUARIO
            session["admin"] = True
            session["role"] = "admin"

            return redirect(
                url_for("dashboard")
            )

        # USUÁRIO NORMAL

        usuario_correto = hmac.compare_digest(
            usuario,
            USUARIO
        )

        senha_correta = hmac.compare_digest(
            senha,
            USUARIO_SENHA
        )

        if (
            usuario_correto
            and senha_correta
        ):

            session.clear()

            session["usuario"] = USUARIO
            session["admin"] = False
            session["role"] = "usuario"

            return redirect(
                url_for("dashboard")
            )

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
        usuario=session.get("usuario"),
        admin=usuario_admin(),
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    acesso = exigir_admin()

    if acesso:
        return acesso

    total_arquivos = 0
    total_python = 0

    os.makedirs(
        ARQUIVOS_DIR,
        exist_ok=True
    )

    for raiz, diretorios, ficheiros in os.walk(
        ARQUIVOS_DIR
    ):

        for ficheiro in ficheiros:

            total_arquivos += 1

            if ficheiro.lower().endswith(".py"):
                total_python += 1

    return render_template(
        "admin.html",
        usuario=session.get("usuario"),
        total_arquivos=total_arquivos,
        total_python=total_python,
    )


# =========================================================
# ADMIN INFO
# =========================================================

@app.route("/admin-info")
def admin_info():

    acesso = exigir_admin()

    if acesso:
        return acesso

    total_arquivos = 0
    total_python = 0

    os.makedirs(
        ARQUIVOS_DIR,
        exist_ok=True
    )

    for raiz, diretorios, ficheiros in os.walk(
        ARQUIVOS_DIR
    ):

        for ficheiro in ficheiros:

            total_arquivos += 1

            if ficheiro.lower().endswith(".py"):
                total_python += 1

    html = f"""
<!DOCTYPE html>
<html lang="pt">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Painel de Administrador</title>

<style>

body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f2f4f7;
}}

header {{
    background: #1f2937;
    color: white;
    padding: 25px;
    text-align: center;
}}

.container {{
    max-width: 900px;
    margin: 30px auto;
    padding: 20px;
}}

.cards {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}}

.card {{
    background: white;
    padding: 30px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,.1);
}}

.numero {{
    font-size: 40px;
    font-weight: bold;
    color: #2563eb;
}}

a {{
    display: inline-block;
    margin-top: 25px;
    background: #2563eb;
    color: white;
    padding: 12px 20px;
    border-radius: 6px;
    text-decoration: none;
}}

</style>

</head>

<body>

<header>

<h1>⚙️ Painel de Administrador</h1>

<p>👑 {session.get("usuario")}</p>

</header>

<div class="container">

<div class="cards">

<div class="card">

<h2>📁 Ficheiros</h2>

<div class="numero">
{total_arquivos}
</div>

</div>

<div class="card">

<h2>🐍 Python</h2>

<div class="numero">
{total_python}
</div>

</div>

</div>

<a href="{url_for('dashboard')}">
← Voltar ao Dashboard
</a>

</div>

</body>
</html>
"""

    return html


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

    os.makedirs(
        ARQUIVOS_DIR,
        exist_ok=True
    )

    lista = []

    try:

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

                relativo = relativo.replace(
                    os.sep,
                    "/"
                )

                lista.append(
                    relativo
                )

    except OSError as e:

        flash(
            f"Erro ao listar os ficheiros: {e}",
            "erro"
        )

        lista = []

    lista.sort(
        key=lambda x: x.lower()
    )

    return render_template(
        "arquivos.html",
        arquivos=lista,
        admin=usuario_admin(),
    )


# =========================================================
# VISUALIZAR / ABRIR ARQUIVO
# =========================================================

@app.route(
    "/visualizar/<path:nome>"
)
def visualizar(nome):

    if not usuario_logado():
        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # VALIDAR CAMINHO
    # -----------------------------------------------------

    caminho = caminho_seguro(nome)

    if caminho is None:

        abort(404)

    # -----------------------------------------------------
    # VERIFICAR SE EXISTE
    # -----------------------------------------------------

    if not os.path.exists(caminho):

        flash(
            "Ficheiro não encontrado.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    # -----------------------------------------------------
    # NÃO PERMITIR ABRIR DIRETÓRIO
    # -----------------------------------------------------

    if not os.path.isfile(caminho):

        flash(
            "O caminho informado não é um ficheiro.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

    # -----------------------------------------------------
    # ARQUIVOS PYTHON
    # -----------------------------------------------------

    if arquivo_e_py(nome):

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as f:

                conteudo = f.read()

        except UnicodeDecodeError:

            flash(
                "Não foi possível ler o ficheiro Python.",
                "erro"
            )

            return redirect(
                url_for("arquivos")
            )

        except OSError as e:

            flash(
                f"Erro ao ler o ficheiro: {e}",
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
            somente_visualizacao=not usuario_admin(),
        )

    # -----------------------------------------------------
    # OUTROS ARQUIVOS
    # -----------------------------------------------------

    tipo_mime, _ = mimetypes.guess_type(
        caminho
    )

    if not tipo_mime:
        tipo_mime = "application/octet-stream"

    # -----------------------------------------------------
    # ENVIAR ARQUIVO DIRETAMENTE
    # -----------------------------------------------------

    try:

        return send_file(
            caminho,
            mimetype=tipo_mime,
            as_attachment=False,
            conditional=True
        )

    except OSError:

        flash(
            "Não foi possível abrir o ficheiro.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )


# =========================================================
# DOWNLOAD FORÇADO
# =========================================================

@app.route(
    "/download/<path:nome>"
)
def download(nome):

    if not usuario_logado():
        return redirect(
            url_for("login")
        )

    caminho = caminho_seguro(nome)

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

    nome_download = os.path.basename(
        caminho
    )

    try:

        return send_file(
            caminho,
            as_attachment=True,
            download_name=nome_download,
            conditional=True
        )

    except OSError:

        flash(
            "Não foi possível fazer o download.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )


# =========================================================
# EDITAR PY
# SOMENTE ADMIN
# =========================================================

@app.route(
    "/editar/<path:nome>",
    methods=["POST"]
)
def editar(nome):

    acesso = exigir_admin()

    if acesso:
        return acesso

    if not arquivo_e_py(nome):

        flash(
            "Somente ficheiros .py podem ser editados.",
            "erro"
        )

        return redirect(
            url_for("arquivos")
        )

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

    caminho = caminho_seguro(nome)

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

            f.write(conteudo)

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
# SOMENTE ADMIN
# =========================================================

@app.route(
    "/novo-arquivo",
    methods=["GET", "POST"]
)
def novo_arquivo():

    acesso = exigir_admin()

    if acesso:
        return acesso

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

        caminho = caminho_seguro(nome)

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
# UPLOAD
# SOMENTE ADMIN
# =========================================================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload():

    acesso = exigir_admin()

    if acesso:
        return acesso

    if request.method == "POST":

        ficheiro = request.files.get(
            "arquivo"
        )

        if ficheiro is None:

            flash(
                "Nenhum ficheiro selecionado.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        nome_original = ficheiro.filename

        if not nome_original:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        nome = nome_arquivo_seguro(
            nome_original
        )

        if nome is None:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # SOMENTE PYTHON

        if not nome.lower().endswith(".py"):

            flash(
                "Somente ficheiros .py podem ser enviados.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        # PROTEGER APP.PY

        if app_py_protegido(nome):

            flash(
                "O ficheiro app.py está protegido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        caminho = caminho_seguro(nome)

        if caminho is None:

            flash(
                "Nome de ficheiro inválido.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        if os.path.exists(caminho):

            flash(
                "Esse ficheiro já existe. "
                "Use o editor para alterar o ficheiro.",
                "erro"
            )

            return redirect(
                url_for("upload")
            )

        try:

            os.makedirs(
                os.path.dirname(caminho),
                exist_ok=True
            )

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
# EXCLUIR PY
# SOMENTE ADMIN
# =========================================================

@app.route(
    "/excluir/<path:nome>",
    methods=["POST"]
)
def excluir(nome):

    acesso = exigir_admin()

    if acesso:
        return acesso

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

    caminho = caminho_seguro(nome)

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

        os.remove(caminho)

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
# ERRO 413
# =========================================================

@app.errorhandler(413)
def arquivo_muito_grande(error):

    flash(
        "O ficheiro é demasiado grande. "
        "O limite é 16 MB.",
        "erro"
    )

    if usuario_logado():

        return redirect(
            url_for("upload")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# ERRO 404
# =========================================================

@app.errorhandler(404)
def pagina_nao_encontrada(error):

    if usuario_logado():

        flash(
            "Página ou ficheiro não encontrado.",
            "erro"
        )

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# ERRO 500
# =========================================================

@app.errorhandler(500)
def erro_interno(error):

    app.logger.exception(
        "Erro interno do servidor"
    )

    if usuario_logado():

        flash(
            "Ocorreu um erro interno ao processar o pedido.",
            "erro"
        )

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# EXECUTAR
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

