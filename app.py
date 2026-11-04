from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Força o Flask a achar a pasta templates de forma absoluta (evita erro no Render)
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

DB = 'grupos.db'
SENHA_ADMIN = 'suasenha123'  # troque depois

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS grupos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT NOT NULL,
        link TEXT NOT NULL,
        plataforma TEXT NOT NULL,
        categoria_id INTEGER NOT NULL,
        destaque INTEGER DEFAULT 0,
        aprovado INTEGER DEFAULT 0,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (categoria_id) REFERENCES categorias(id))''')

    categorias_iniciais = [
        ('Amizade', 'amizade'),
        ('Ofertas', 'ofertas'),
        ('Games', 'games'),
        ('Trabalho', 'trabalho'),
        ('Namoro', 'namoro'),
        ('Tecnologia', 'tecnologia'),
        ('Frases', 'frases'),
    ]
    for nome, slug in categorias_iniciais:
        c.execute('INSERT OR IGNORE INTO categorias (nome, slug) VALUES (?, ?)', (nome, slug))

    conn.commit()
    conn.close()

@app.route('/')
def home():
    conn = get_db()
    grupos = conn.execute('''SELECT g.*, c.nome AS cat_nome, c.slug AS cat_slug
        FROM grupos g JOIN categorias c ON g.categoria_id = c.id
        WHERE g.aprovado = 1
        ORDER BY g.destaque DESC, g.id DESC''').fetchall()
    categorias = conn.execute('SELECT * FROM categorias ORDER BY nome').fetchall()
    conn.close()
    return render_template('index.html', grupos=grupos, categorias=categorias)

@app.route('/categoria/<slug>')
def categoria(slug):
    conn = get_db()
    cat = conn.execute('SELECT * FROM categorias WHERE slug = ?', (slug,)).fetchone()
    if not cat:
        conn.close()
        return 'Categoria não encontrada', 404
    grupos = conn.execute('''SELECT g.*, c.nome AS cat_nome, c.slug AS cat_slug
        FROM grupos g JOIN categorias c ON g.categoria_id = c.id
        WHERE g.aprovado = 1 AND g.categoria_id = ?
        ORDER BY g.destaque DESC, g.id DESC''', (cat['id'],)).fetchall()
    categorias = conn.execute('SELECT * FROM categorias ORDER BY nome').fetchall()
    conn.close()
    return render_template('index.html', grupos=grupos, categorias=categorias, categoria_atual=cat['nome'])

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    conn = get_db()
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        descricao = request.form['descricao'].strip()
        link = request.form['link'].strip()
        plataforma = request.form['plataforma']
        categoria_id = request.form['categoria_id']

        if plataforma not in ('whatsapp', 'telegram'):
            conn.close()
            return 'Plataforma inválida', 400

        if plataforma == 'whatsapp' and 'chat.whatsapp.com' not in link:
            conn.close()
            return 'Link de WhatsApp inválido. Use um link chat.whatsapp.com', 400
        if plataforma == 'telegram' and 't.me/' not in link:
            conn.close()
            return 'Link de Telegram inválido. Use um link t.me/', 400

        conn.execute('''INSERT INTO grupos (titulo, descricao, link, plataforma, categoria_id)
            VALUES (?, ?, ?, ?, ?)''', (titulo, descricao, link, plataforma, categoria_id))
        conn.commit()
        conn.close()
        return render_template('cadastrar.html', categorias=[], sucesso=True)

    categorias = conn.execute('SELECT * FROM categorias ORDER BY nome').fetchall()
    conn.close()
    return render_template('cadastrar.html', categorias=categorias, sucesso=False)

@app.route('/admin')
def admin():
    if request.args.get('senha') != SENHA_ADMIN:
        return 'Acesso negado', 403
    conn = get_db()
    pendentes = conn.execute('''SELECT g.*, c.nome AS cat_nome
        FROM grupos g JOIN categorias c ON g.categoria_id = c.id
        WHERE g.aprovado = 0 ORDER BY g.id DESC''').fetchall()
    aprovados = conn.execute('''SELECT g.*, c.nome AS cat_nome
        FROM grupos g JOIN categorias c ON g.categoria_id = c.id
        WHERE g.aprovado = 1 ORDER BY g.id DESC''').fetchall()
    conn.close()
    return render_template('admin.html', pendentes=pendentes, aprovados=aprovados, senha=SENHA_ADMIN)

@app.route('/aprovar/<int:id>')
def aprovar(id):
    if request.args.get('senha') != SENHA_ADMIN:
        return 'Acesso negado', 403
    conn = get_db()
    conn.execute('UPDATE grupos SET aprovado = 1 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', senha=SENHA_ADMIN))

@app.route('/remover/<int:id>')
def remover(id):
    if request.args.get('senha') != SENHA_ADMIN:
        return 'Acesso negado', 403
    conn = get_db()
    conn.execute('DELETE FROM grupos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', senha=SENHA_ADMIN))

@app.route('/destacar/<int:id>')
def destacar(id):
    if request.args.get('senha') != SENHA_ADMIN:
        return 'Acesso negado', 403
    conn = get_db()
    conn.execute('UPDATE grupos SET destaque = 1 - destaque WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', senha=SENHA_ADMIN))

# Garante que o banco de dados seja criado quando o Render iniciar o app
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
