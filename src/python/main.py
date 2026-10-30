import json
import re
import time
import numpy as np
from pyodide.ffi import create_proxy
from pyscript import document

INICIO = time.time()

# ---------- Dados ----------
with open("dados.json", encoding="utf-8") as f:
    DADOS = json.load(f)
FRUTAS = DADOS["frutas"]
CRITERIOS = DADOS["criterios"]
MATRIZ = np.array([x["vetor"] for x in FRUTAS], dtype=float)  # embeddings

# ---------- Telemetria ----------
TEL = {"buscas": 0, "bloqueios": 0, "recomendacoes": 0, "ultima_acao": "-"}


def atualiza_telemetria():
    decorrido = round((time.time() - INICIO) * 1000)
    linhas = [
        ("Frutas carregadas", len(FRUTAS)),
        ("Buscas feitas", TEL["buscas"]),
        ("Entradas bloqueadas", TEL["bloqueios"]),
        ("Recomendações", TEL["recomendacoes"]),
        ("Última ação", TEL["ultima_acao"]),
        ("Tempo de sessão", f"{decorrido} ms"),
    ]
    el = document.getElementById("tel")
    el.innerHTML = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in linhas)


# ---------- Guardrails ----------
PADRAO = re.compile(r"^[A-Za-zÀ-ÿ ]+$")


def valida_busca(texto):
    """Retorna (ok, mensagem)."""
    texto = texto.strip()
    if len(texto) > 30:
        return False, "Use no máximo 30 caracteres."
    if texto and not PADRAO.match(texto):
        return False, "Digite apenas letras e espaços."
    return True, ""


def valida_preferencias(valores):
    return all(0 <= v <= 10 for v in valores)


# ---------- Interface ----------
def mostra_aviso(msg):
    document.getElementById("aviso").textContent = msg


def desenha_grade(lista):
    grade = document.getElementById("grade")
    grade.innerHTML = ""
    if not lista:
        grade.innerHTML = "<p>Nenhuma fruta encontrada. Tente outro nome.</p>"
        return
    for fruta in lista:
        b = document.createElement("button")
        b.className = "card"
        b.type = "button"
        b.innerHTML = (
            f'<img src="{fruta["imagem"]}" alt="{fruta["nome"]}">'
            f'<strong>{fruta["nome"]}</strong><span>R$ {fruta["preco_kg"]:.2f}/kg</span>'
        )
        b.addEventListener("click", create_proxy(lambda e, f=fruta: mostra_detalhe(f)))
        grade.appendChild(b)


def mostra_detalhe(fruta):
    TEL["ultima_acao"] = f"Detalhe: {fruta['nome']}"
    barras = "".join(
        f'<div>{c}</div><div class="barra"><i style="width:{v * 10}%"></i></div>'
        for c, v in zip(CRITERIOS, fruta["vetor"])
    )
    baixo = " (estoque baixo)" if fruta["estoque_kg"] < 20 else ""
    document.getElementById("detalhe").innerHTML = (
        f'<img src="{fruta["imagem"]}" alt="{fruta["nome"]}">'
        f'<h3>{fruta["nome"]}</h3>'
        f'<p>{fruta["categoria"]} · R$ {fruta["preco_kg"]:.2f}/kg · '
        f'{fruta["estoque_kg"]} kg em estoque{baixo}</p>{barras}'
    )
    atualiza_telemetria()


def buscar(evento=None):
    texto = document.getElementById("busca").value
    ok, msg = valida_busca(texto)
    mostra_aviso(msg)
    if not ok:
        TEL["bloqueios"] += 1
        TEL["ultima_acao"] = "Busca bloqueada"
        atualiza_telemetria()
        return
    TEL["buscas"] += 1
    TEL["ultima_acao"] = f"Busca: {texto.strip() or '(todas)'}"
    termo = texto.strip().lower()
    desenha_grade([f for f in FRUTAS if termo in f["nome"].lower()])
    atualiza_telemetria()


# funcao para um caminho de administrador em uma futura atualização do projeto
'''def adiciona_frutas():
    f = input("Qual fruta você procura? ")
    if f not in FRUTAS:
        print("A fruta que você procura não aparece.")
        resposta = input("Deseja adicionar fruta? [s/n]: ").lower()
        if resposta == 's':
            nova_fruta = {
                "id": max((fruta["id"] for fruta in FRUTAS), default=0) + 1,
                "nome": f,
                "categoria": input("Categoria da fruta: "),
                "preco_kg": float(input("Preço por kg: ")),
                "estoque_kg": float(input("Estoque em kg: ")),
                "imagem": input("Caminho da imagem: "),
                "vetor": []
            }
            FRUTAS.append(nova_fruta)
            with open("dados.json", "w", encoding="utf-8") as arquivo:
                json.dump(FRUTAS, arquivo, ensure_ascii=False, indent=4)
            print(f"{f} adicionada com sucesso!")
        else:
            print("Fruta não adicionada.")
    else:
        print("Essa fruta já está cadastrada!")'''


def recomendar(evento=None):
    valores = [float(document.getElementById(f"s{i}").value) for i in range(len(CRITERIOS))]
    if not valida_preferencias(valores):
        mostra_aviso("Use valores de 0 a 10.")
        TEL["bloqueios"] += 1
        atualiza_telemetria()
        return
    alvo = np.array(valores)
    distancias = np.linalg.norm(MATRIZ - alvo, axis=1)  # norma euclidiana
    ordem = np.argsort(distancias)[:3]
    TEL["recomendacoes"] += 1
    TEL["ultima_acao"] = "Recomendação"
    document.getElementById("resultado").innerHTML = "".join(
        f'<li><strong>{FRUTAS[i]["nome"]}</strong> <small>distância {distancias[i]:.2f}</small></li>'
        for i in ordem
    )
    atualiza_telemetria()


def monta_sliders():
    html = ""
    for i, c in enumerate(CRITERIOS):
        html += (
            f'<div class="slider"><label for="s{i}">{c.capitalize()}</label>'
            f'<output id="o{i}">5</output>'
            f'<input id="s{i}" type="range" min="0" max="10" value="5"></div>'
        )
    document.getElementById("sliders").innerHTML = html
    for i in range(len(CRITERIOS)):
        s = document.getElementById(f"s{i}")
        s.addEventListener(
            "input",
            create_proxy(lambda e, i=i: setattr(document.getElementById(f"o{i}"), "textContent", e.target.value)),
        )


# ---------- Início ----------
monta_sliders()
desenha_grade(FRUTAS)
document.getElementById("btn-buscar").addEventListener("click", create_proxy(buscar))
document.getElementById("busca").addEventListener(
    "keydown", create_proxy(lambda e: buscar() if e.key == "Enter" else None)
)
document.getElementById("btn-rec").addEventListener("click", create_proxy(recomendar))
atualiza_telemetria()
