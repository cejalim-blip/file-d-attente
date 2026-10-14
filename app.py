# -*- coding: utf-8 -*-
"""
Relais public — Centre d'Entraide de Jette.

Petit service distant (a deployer sur Railway, Render, etc.).
Role UNIQUE : recevoir l'etat public pousse par le PC local et le servir
aux smartphones, en lecture seule. Il n'a AUCUN acces a l'administration
ni a la base de donnees locale.

Securite :
  - L'ecriture (/api/push) exige une cle secrete partagee (variable
    d'environnement RELAY_KEY).
  - La lecture publique n'expose que : numero courant, derniers appels,
    nombre en attente, statut, message. Aucune donnee personnelle.

Variables d'environnement :
  - RELAY_KEY : cle secrete partagee avec le PC local (obligatoire).
  - PORT      : fourni automatiquement par l'hebergeur.
"""

import os
import json
import time
import queue
import threading

from flask import Flask, request, jsonify, Response, render_template_string

app = Flask(__name__)

RELAY_KEY = os.environ.get("RELAY_KEY", "")

# Dernier etat recu (en memoire). Si le service redemarre, il attend un
# nouveau push du PC local (qui pousse a chaque changement).
_etat = {
    "numero_courant": None,
    "derniers": [],
    "en_attente": 0,
    "statut": "en_cours",
    "message": "",
    "nom": "Centre d'Entraide de Jette - ASBL",
    "maj": None,
}
_lock = threading.Lock()
_abonnes = []


def _diffuser():
    donnees = json.dumps(_etat, ensure_ascii=False)
    with _lock:
        morts = []
        for q in _abonnes:
            try:
                q.put_nowait(donnees)
            except queue.Full:
                morts.append(q)
        for q in morts:
            _abonnes.remove(q)


@app.route("/api/push", methods=["POST"])
def push():
    """Reçoit l'etat public depuis le PC local."""
    data = request.get_json(silent=True) or {}
    if RELAY_KEY and data.get("cle") != RELAY_KEY:
        return jsonify({"ok": False, "message": "Clé invalide"}), 403
    etat = data.get("etat")
    if not isinstance(etat, dict):
        return jsonify({"ok": False, "message": "État manquant"}), 400
    global _etat
    # On ne conserve que les champs publics attendus
    champs = ("numero_courant", "derniers", "en_attente", "statut", "message", "nom", "maj")
    with _lock:
        _etat = {k: etat.get(k, _etat.get(k)) for k in champs}
    _diffuser()
    return jsonify({"ok": True})


@app.route("/api/etat_public")
def etat_public():
    with _lock:
        return jsonify(_etat)


@app.route("/flux_public")
def flux_public():
    def generer():
        q = queue.Queue(maxsize=20)
        with _lock:
            _abonnes.append(q)
        try:
            yield f"data: {json.dumps(_etat, ensure_ascii=False)}\n\n"
            while True:
                try:
                    donnees = q.get(timeout=20)
                    yield f"data: {donnees}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        except GeneratorExit:
            pass
        finally:
            with _lock:
                if q in _abonnes:
                    _abonnes.remove(q)
    return Response(generer(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# Le relais sert sa propre copie de la page publique (autonome, sans fichiers
# externes). Le logo est servi par une route dediee si fourni, sinon texte.
PAGE = None
LOGO_DATA = None


def _charger_page():
    global PAGE, LOGO_DATA
    ici = os.path.dirname(os.path.abspath(__file__))
    chemin = os.path.join(ici, "suivi_relais.html")
    with open(chemin, "r", encoding="utf-8") as f:
        PAGE = f.read()
    # Logo optionnel (depose a cote du relais)
    for nom in ("logo.png", "logo.jpg", "logo.svg"):
        p = os.path.join(ici, nom)
        if os.path.exists(p):
            LOGO_DATA = (p, nom)
            break


@app.route("/")
@app.route("/suivi")
def suivi():
    if PAGE is None:
        _charger_page()
    return render_template_string(PAGE)


@app.route("/logo")
def logo():
    if LOGO_DATA is None:
        # SVG minimal si aucun logo fourni
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
               '<rect width="100" height="100" rx="12" fill="#1a6b54"/>'
               '<text x="50" y="58" font-size="40" fill="#fff" text-anchor="middle"'
               ' font-family="Arial">CE</text></svg>')
        return Response(svg, mimetype="image/svg+xml")
    chemin, nom = LOGO_DATA
    from flask import send_file
    return send_file(chemin)


@app.route("/sante")
def sante():
    return jsonify({"ok": True, "maj": _etat.get("maj")})


if __name__ == "__main__":
    _charger_page()
    port = int(os.environ.get("PORT", 8090))
    app.run(host="0.0.0.0", port=port, threaded=True)
