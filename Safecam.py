import base64
import os
import re
import time
import requests

# =========================================================================
# CONFIGURATION GREEN API ET GROQ VISION (REST API)
# =========================================================================
ID_INSTANCE = "710722692500"
API_TOKEN = "795c19e1e8ba4947976597f271b662b0cecd8bf576f44b6b87"

# REMPLACE CETTE VALEUR PAR TA VRAIE CLÉ GROQ (ex: "gsk_...")
GROQ_API_KEY = "gsk_VOTRE_CLE_GROQ_ICI"

URL_RECEVOIR = (
    f"https://api.green-api.com/waInstance{ID_INSTANCE}/receiveNotification/{API_TOKEN}"
)
URL_SUPPRIMER = (
    f"https://api.green-api.com/waInstance{ID_INSTANCE}/deleteNotification/{API_TOKEN}"
)
URL_ENVOYER = (
    f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
)
URL_TELECHARGER = (
    f"https://api.green-api.com/waInstance{ID_INSTANCE}/downloadFile/{API_TOKEN}"
)

# Endpoint d'API HTTP REST direct pour Groq
URL_GROQ_CHAT = "https://api.groq.com/openai/v1/chat/completions"

# =========================================================================
# MESSAGES D'ACCUEIL, DE SECURITE ET DE MENUS
# =========================================================================
MESSAGE_ACCUEIL = """🛡️ *Bienvenue sur SafeCam V3 - CyberSécurité Cameroun*

Je suis ton assistant virtuel intelligent spécialisé dans la détection des arnaques et la protection contre la cyberfraude au Cameroun.

*Que souhaites-tu faire ?*

1️⃣ *Scanner un message* (Transfère-moi le texte suspect)
2️⃣ *Scanner un lien / site web* (Envoie l'adresse URL du site)
3️⃣ *Signaler une arnaque* (Partage le numéro de l'arnaqueur et sa méthode)
4️⃣ *Conseils & Sécurité* (Guide de prévention rapide)

💡 _Astuce : Tu peux aussi me transférer directement une capture d'écran, un SMS, un reçu ou un lien suspect à tout moment !_"""

MESSAGE_REFUS_SECURITE = """🤖 *Système de Sécurité SafeCam*

J'essaie toujours d'être utile, mais mes contrôles de sécurité et de confidentialité m'empêchent de répondre à cette demande ou de partager les réglages internes du système. 

Si tu as un message, une capture d'écran, un numéro ou un lien suspect à scanner, je peux t'aider ! 🛡️"""

MESSAGE_SIGNALEMENT_GUIDE = """🚨 *Signaler une Arnaque (SafeCam Base)*

Pour enregistrer une arnaque dans notre base de données, réponds avec le format suivant :

*Numéro de l'arnaqueur :* +237XXXXXXXXX
*Type d'arnaque :* Mobile Money / Faux concours / Offre d'emploi
*Description :* (Raconte brièvement ce qu'il a tenté de faire)

Merci de contribuer à la sécurité de la communauté Camerounaise ! 🇨🇲"""

MESSAGE_CONSEILS = """💡 *Conseils de Sécurité de SafeCam V3*

1. ⚠️ *Aucune entreprise* (Orange, MTN, Dôvv, Banque) ne donne de l'argent gratuit via des liens Web étranges.
2. 🔒 Ne donnez *JAMAIS* votre code secret Mobile Money ou vos codes OTP reçus par SMS.
3. 🌐 Vérifiez toujours le nom de domaine des sites : les vrais sites se terminent souvent par `.cm`, `.com` ou `.fr`. Attention aux domaines comme `.buzz`, `.xyz`, `.top`.
4. 📵 En cas de doute, appelez directement le service client officiel."""

# =========================================================================
# BASE DE DONNEES SAFECAM V3
# =========================================================================
FAMILLES_ARNAQUES = {
    "famille_1": {
        "nom_famille": "Famille 1 : L'appât du gain & Mobile Money",
        "types_arnaques": {
            "erreur_transfert": {
                "nom_type": "Type 1 : Erreur de transfert MoMo/Orange Money",
                "mots_cles": [
                    "erreur",
                    "renvoie",
                    "transfert par erreur",
                    "retrait",
                    "tu t'es trompe",
                    "trompee",
                ],
                "score": 50,
                "parade": (
                    "PARADE : Compose ton code secret opérateur (ex: *126# ou"
                    " #150#) pour vérifier ton solde réel."
                ),
                "conseils": [
                    "Si ton solde n'a pas augmenté, c'est un faux SMS reçu.",
                    "Ne renvoie jamais d'argent à un inconnu.",
                ],
            },
            "vous_avez_gagne": {
                "nom_type": "Type 2 : Faux tirage au sort / Gain de lot",
                "mots_cles": [
                    "gagne",
                    "felicitations",
                    "tirage",
                    "lot",
                    "selectionne",
                    "tombola",
                ],
                "score": 50,
                "parade": (
                    "PARADE : Ne paie jamais pour entrer en possession d'un"
                    " prix ou d'un lot."
                ),
                "conseils": [
                    "Une entreprise sérieuse déduit les frais du prix.",
                    "N'envoie pas ta CNI.",
                ],
            },
            "faux_pret": {
                "nom_type": "Type 3 : Faux prêt Express en ligne",
                "mots_cles": [
                    "pret",
                    "frais d'assurance",
                    "credit rapide",
                    "dossier pret",
                    "credit en 5 min",
                ],
                "score": 40,
                "parade": (
                    "PARADE : Les institutions financières officielles ne"
                    " demandent jamais de dépôt Mobile Money à l'avance."
                ),
                "conseils": [
                    "Les frais de dossier légaux sont directement retenus sur"
                    " le prêt."
                ],
            },
        },
    },
    "famille_2": {
        "nom_famille": "Famille 2 : L'amour, l'héritage et le mysticisme",
        "types_arnaques": {
            "faux_heritage": {
                "nom_type": "Type 4 : Faux héritage / Faux notaire",
                "mots_cles": [
                    "heritage",
                    "notaire",
                    "avocat",
                    "debloquer les fonds",
                    "succession",
                    "millions",
                    "coffre",
                ],
                "score": 80,
                "parade": (
                    "PARADE : Aucun avocat ou notaire sérieux ne gère un dossier"
                    " d'héritage via WhatsApp."
                ),
                "conseils": [
                    "Exige un rendez-vous physique dans un vrai cabinet"
                    " juridique."
                ],
            },
            "arnaque_sentimentale": {
                "nom_type": "Type 5 : Arnaque sentimentale / Brouteur",
                "mots_cles": [
                    "mon amour",
                    "je t'aime",
                    "bebe",
                    "cheri",
                    "visa",
                    "billet d'avion",
                    "envoie moi",
                    "besoin d'argent pour soigner",
                ],
                "score": 60,
                "parade": (
                    "PARADE : Ne verse jamais d'argent à un contact virtuel"
                    " rencontré sur Internet."
                ),
                "conseils": [
                    "Les cybercriminels utilisent de fausses photos et des voix"
                    " générées par IA."
                ],
            },
            "faux_marabout": {
                "nom_type": (
                    "Type 6 : Multiplicateurs d'argent / Portefeuille magique"
                ),
                "mots_cles": [
                    "marabout",
                    "portefeuille magique",
                    "rituel",
                    "multiplication",
                    "bedou magique",
                    "richesse rapide",
                ],
                "score": 50,
                "parade": (
                    "PARADE : La création ou multiplication magique d'argent"
                    " n'existe pas."
                ),
                "conseils": [
                    "C'est un piège d'extorsion psychologique qui peut mettre"
                    " ta vie en danger."
                ],
            },
        },
    },
    "famille_3": {
        "nom_famille": "Famille 3 : La fausse aide et l'usurpation d'identité",
        "types_arnaques": {
            "faux_agent": {
                "nom_type": (
                    "Type 7 : Faux agent de service client (MTN, Orange,"
                    " Camtel, Banque)"
                ),
                "mots_cles": [
                    "agent mtn",
                    "service client",
                    "code secret",
                    "code pin",
                    "validation",
                    "confirmation",
                    "compte bloque",
                ],
                "score": 50,
                "parade": (
                    "PARADE : Un conseiller client officiel ne te demandera"
                    " JAMAIS ton code secret PIN ou OTP."
                ),
                "conseils": [
                    "Raccroche immédiatement et appelle les numéros"
                    " d'assistance officiels."
                ],
            },
            "piratage_proche": {
                "nom_type": (
                    "Type 8 : Usurpation d'un proche / Faux dépannage urgent"
                ),
                "mots_cles": [
                    "coucou",
                    "nouveau numero",
                    "hopital",
                    "accident",
                    "urgence",
                    "depanne",
                    "je suis en panne",
                    "mon autre telephone",
                ],
                "score": 80,
                "parade": (
                    "PARADE : Joins la personne directement sur son ANCIEN"
                    " numéro habituel pour vérifier."
                ),
                "conseils": ["Demande-lui un message vocal en disant un mot secret."],
            },
            "vol_compte_whatsapp": {
                "nom_type": (
                    "Type 9 : Piratage et Vol de compte WhatsApp (Code OTP)"
                ),
                "mots_cles": [
                    "envoie le code",
                    "code a 6 chiffres",
                    "code de verification",
                    "sms que tu as recu",
                    "code whatsapp",
                ],
                "score": 95,
                "parade": (
                    "PARADE : Ne partage JAMAIS un code d'authentification reçu"
                    " par SMS."
                ),
                "conseils": ["Active la double vérification sur WhatsApp."],
            },
        },
    },
    "famille_4": {
        "nom_famille": "Famille 4 : Faux commerces et investissements",
        "types_arnaques": {
            "fausse_boutique": {
                "nom_type": (
                    "Type 10 : Fausse page de vente / Arnaque à la livraison"
                ),
                "mots_cles": [
                    "boutique",
                    "promo",
                    "iphone moins cher",
                    "livraison",
                    "paye d'abord",
                    "article disponible",
                    "avance",
                    "acompte",
                ],
                "score": 60,
                "parade": (
                    "PARADE : Exige le paiement à la livraison après inspection"
                    " de l'article."
                ),
                "conseils": [
                    "Les prix anormalement bas masquent souvent de fausses"
                    " boutiques."
                ],
            },
            "faux_investissement": {
                "nom_type": (
                    "Type 11 : Systèmes pyramidaux & Faux placements"
                    " (Ponzi/Crypto)"
                ),
                "mots_cles": [
                    "opportunite_financiere",
                    "liberte financiere",
                    "crypto_monnaie",
                    "bitcoin",
                    "trading_rapide",
                    "parrainage",
                    "investissement",
                    "doubler ton argent",
                    "rendement garanti",
                ],
                "score": 85,
                "parade": (
                    "PARADE : Fuis tout système qui t'oblige à recruter d'autres"
                    " personnes pour récupérer tes gains."
                ),
                "conseils": [
                    "L'argent facile n'existe pas. On mange la sueur de son"
                    " front."
                ],
            },
            "arnaque_aux_taches": {
                "nom_type": (
                    "Type 12 : Arnaque aux tâches (Aimer des vidéos"
                    " TikTok/YouTube)"
                ),
                "mots_cles": [
                    "liker des videos",
                    "tache payee",
                    "gagner de l'argent en likant",
                    "commission telegram",
                    "travailler sur tiktok",
                ],
                "score": 75,
                "parade": (
                    "PARADE : C'est un piège où on te donne 1000 F au début pour"
                    " te mettre en confiance."
                ),
                "conseils": ["Ne bascule jamais vers leurs groupes VIP payants."],
            },
        },
    },
    "famille_5": {
        "nom_famille": "Famille 5 : Phishing Technique et Bourses",
        "types_arnaques": {
            "bourses_etudes": {
                "nom_type": "Type 13 : Fausse bourse d'études à l'étranger",
                "mots_cles": [
                    "bourse d'etude",
                    "immigration canada",
                    "visa garanti",
                    "travailler au canada",
                    "admission universite",
                ],
                "score": 70,
                "parade": (
                    "PARADE : Les vrais programmes ne passent pas par des"
                    " personnes individuelles sur WhatsApp."
                ),
                "conseils": [
                    "Vérifiez toujours auprès de l'ambassade officielle.",
                    "Ne payez pas de frais non officiels.",
                ],
            },
            "quishing_et_liens": {
                "nom_type": (
                    "Type 14 : Faux sites bancaires / Vol de session web"
                ),
                "mots_cles": [
                    "cliquez ici",
                    "connectez-vous sur",
                    "mis a jour de votre compte",
                    "http://",
                    "https://bit.ly",
                    "tinyurl.com",
                    ".buzz",
                    ".xyz",
                    ".top",
                    ".site",
                ],
                "score": 50,
                "parade": (
                    "PARADE : Ne te connecte jamais à tes comptes financiers à"
                    " partir d'un lien reçu par message."
                ),
                "conseils": [
                    "Saisis toi-même l'adresse de ton application ou de ta"
                    " banque."
                ],
            },
        },
    },
    "famille_6": {
        "nom_famille": "Famille 6 : Arnaque Gain et Frais d'avance",
        "types_arnaques": {
            "gain_frais_retrait": {
                "nom_type": "Type 15 : Demande de frais pour retirer un gain",
                "mots_cles": [
                    "felicitations vous avez gagne",
                    "vous avez gagne",
                    "500000 fcfa",
                    "500 000 fcfa",
                    "frais de retrait",
                    "frais pour retirer",
                    "envoyez les frais",
                    "cadau",
                    "dovv",
                ],
                "score": 100,
                "parade": (
                    "PARADE : Un vrai lot ne demande JAMAIS de frais d'avance"
                    " pour être retiré. C'est l'arnaque N°1 au Cameroun."
                ),
                "conseils": [
                    "Ne paye jamais pour toucher un gain.",
                    "Bloque et signale le numéro.",
                ],
            }
        },
    },
}

# =========================================================================
# FONCTIONS LOGIQUES, VISION ET SECURITE
# =========================================================================
import re
import unicodedata


def nettoyer_texte(texte):
  """Enlève les accents, les tirets et la ponctuation pour comparer facilement."""
  texte = unicodedata.normalize('NFD', texte).encode('ascii', 'ignore').decode('utf-8')
  texte = texte.lower()
  texte = re.sub(
      r'[^a-z0-9\s]', ' ', texte
  )  # Remplace tirets, points, etc. par des espaces
  return ' '.join(texte.split())


def detecter_question_suspecte_ou_systeme(texte):
  txt = nettoyer_texte(texte)

  # Mots-clés stratégiques : si l'un de ces mots apparaît avec un autre, c'est une tentative de bypass
  mots_cles = [
      # Mots liés au code / systeme
      "prompt",
      "system prompt",
      "code source",
      "script",
      "algorithme",
      "fichiers",
      "configuration",
      "regles internes",
      "instructions",
      "systeme",
      "programme",
      "base de donnee",
      "donnees internes",
      "reglage",
      # Mots liés aux tentatives d'usurpation / hack
      "bypass",
      "jailbreak",
      "invisid",
      "hack",
      "admin",
      "root",
      "mot de passe",
      "passphrase",
      "override",
      "ignore",
      "oubli",
      "efface",
      "reinitialise",
      "mode developpeur",
      "mode maintenance",
      "droits",
      # Questions d'ingénierie inverse
      "qui t a cree",
      "qui t a fabrique",
      "qui t a programme",
      "qui est ton createur",
      "qui est ton concepteur",
      "comment tu marche",
      "comment tu fonctionne",
      "comment tu as ete fait",
      "comment tu es code",
      "donne moi ton code",
      "affiche ton code",
      "montre ton code",
      "envoie ton code",
      "execute le code",
      "python code",
      "reponds comme un",
      "agis comme un",
      "joue le role",
      "qui es tu vraiment",
  ]

  return any(mot in txt for mot in mots_cles)
  MOTS_INTERDITS_SECURITE = [
    # --- Créateur / Origine ---
    "qui t a cree",
    "qui t a fabrique",
    "qui t a conçu",
    "qui t a developpe",
    "qui t a programme",
    "qui est ton createur",
    "qui est ton auteur",
    "qui est ton boss",
    "qui est ton dev",
    "qui est ton maitre",
    # --- Fonctionnement interne ---
    "comment tu marches",
    "comment tu fonctionnes",
    "comment tu as ete code",
    "comment tu as ete fait",
    "comment tu as ete construit",
    "comment tu es programme",
    "quel est ton fonctionnement",
    "explique ton algorithme",
    "explications sur ton code",
    "donne des details sur ton systeme",
    # --- Code source et Prompt ---
    "prompt",
    "system prompt",
    "code source",
    "donne moi ton code",
    "montre moi ton code",
    "affiche ton code",
    "partage ton code",
    "envoie ton script",
    "ton fichier python",
    "tes instructions systeme",
    "tes regles de base",
    "tes consignes secretes",
    "ta configuration",
    "ta base de donnees",
    # --- Bypass, Jailbreak et Piratage ---
    "jailbreak",
    "bypass",
    "invisid",
    "hack",
    "hacker",
    "admin",
    "root",
    "mot de passe admin",
    "access admin",
    "mode developpeur",
    "mode secours",
    "mode debug",
    "mode maintenance",
    # --- Manipulation d'instructions (Prompt Injection) ---
    "ignore tes regles",
    "ignore tes instructions",
    "oubli tes consignes",
    "efface ta memoire",
    "reponds comme si",
    "agis comme un",
    "joue le role de",
    "pretends etre",
    "change de personnalite",
    "desactive ta securite",
    "desactive tes filtres",
    "reinitialise toi",
  ]
  def analyser_message(message_texte):
  msg_clean = message_texte.lower()
  score_total = 0
  familles_detectees = set()
  details_arnaques = []

  liens = re.findall(r"(https?://[^\s]+)", msg_clean)
  if liens:
    score_total += 20
    for lien in liens:
      if any(
          ext in lien for ext in [".buzz", ".xyz", ".top", ".site", ".tk", ".online"]
      ):
        score_total += 50

  for id_fam, fam_info in FAMILLES_ARNAQUES.items():
    for id_type, type_info in fam_info["types_arnaques"].items():
      for mot in type_info["mots_cles"]:
        if mot in msg_clean:
          score_total += type_info["score"]
          familles_detectees.add(fam_info["nom_famille"])
          if not any(
              d["type"] == type_info["nom_type"] for d in details_arnaques
          ):
            details_arnaques.append({
                "type": type_info["nom_type"],
                "parade_specifique": type_info["parade"],
                "conseils_specifiques": type_info["conseils"],
            })
          break

  if score_total > 100:
    score_total = 100

  if score_total >= 70:
    verdict = (
        "🚨 DANGER CRITIQUE : Cyberfraude ou Arnaque hautement probable !"
    )
  elif score_total >= 35:
    verdict = "⚠️ ATTENTION : Message suspect, restez vigilant."
  else:
    verdict = (
        "✅ ANALYSE : Aucun indicateur majeur de fraude détecté sur ce texte."
    )

  return {
      "verdict": verdict,
      "score_risques": f"{score_total}/100",
      "familles_touchees": list(familles_detectees),
      "analyse_detaillee": details_arnaques,
  }


def analyser_image_avec_groq(chemin_image):
  """Analyse l'image directement via des requêtes HTTP (sans avoir besoin du package 'groq')"""
  try:
    with open(chemin_image, "rb") as img_file:
      img_b64 = base64.b64encode(img_file.read()).decode("utf-8")

    prompt = """
        Tu es l'expert en cybersécurité de SafeCam V3 au Cameroun.
        Analyse cette image ou capture d'écran envoyée par une victime potentielle.
        
        Rédige ta réponse de façon claire sur WhatsApp avec cette structure exacte :
        🛡️ *SafeCam V3 - Analyse d'Image*

        1. 🔍 *Scénario Détecté* : Décris le contexte (ex: Faux SMS MoMo/Orange, Reçu de transfert falsifié, Fausse attestation de gain, etc.).
        2. ⚠️ *Indicateurs Suspects* : Donne 2 à 3 preuves visibles sur l'image qui prouvent la tentative de fraude (polices modifiées, montants/numéros anormaux, fautes).
        3. 💡 *Conseil Immédiat* : Donne l'action urgente à mener par la victime (ex: Ne rien envoyer, vérifier le solde via code USSD officiel *126# ou #150#).
        """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.2-11b-vision-preview",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                },
            ],
        }],
        "temperature": 0.2,
    }

    reponse = requests.post(
        URL_GROQ_CHAT, json=payload, headers=headers, timeout=20
    )

    if reponse.status_code == 200:
      donnees = reponse.json()
      return donnees["choices"][0]["message"]["content"]
    else:
      return (
          f"❌ Erreur d'analyse Groq (Code {reponse.status_code}). Vérifie ta"
          " clé API."
      )

  except Exception as e:
    print(f"Erreur lors du traitement de l'image : {e}")
    return "❌ Erreur interne lors de la lecture de l'image."


def télécharger_fichier_greenapi(download_url, chemin_destination):
  """Télécharge l'image reçue depuis WhatsApp sur le stockage Termux"""
  try:
    res = requests.get(download_url, timeout=15)
    if res.status_code == 200:
      with open(chemin_destination, "wb") as f:
        f.write(res.content)
      return True
  except Exception as e:
    print(f"Erreur de téléchargement : {e}")
  return False


def envoyer_reponse_whatsapp(numero_destinataire, texte_reponse):
  payload = {"chatId": numero_destinataire, "message": texte_reponse}
  headers = {"Content-Type": "application/json"}
  try:
    requests.post(URL_ENVOYER, json=payload, headers=headers, timeout=10)
  except Exception as e:
    print(f"Erreur d'envoi : {e}")


# =========================================================================
# BOUCLE PRINCIPALE
# =========================================================================
print("🚀 SafeCam V3 de Wilson en cours d'exécution sur Termux...")
print(
    "Écoute des messages texte et images WhatsApp démarrée. Appuie sur CTRL+C"
    " pour arrêter."
)

session = requests.Session()

while True:
  try:
    reponse = session.get(URL_RECEVOIR, timeout=10)

    if reponse.status_code == 200 and reponse.json():
      donnees = reponse.json()
      id_notification = donnees.get("receiptId")
      corps = donnees.get("body", {})

      if corps.get("typeWebhook") == "incomingMessageReceived":
        donnees_message = corps.get("messageData", {})
        type_msg = donnees_message.get("typeMessage")
        expediteur = corps["senderData"]["sender"]

        # ---------------------------------------------------------
        # TRAITEMENT DES MESSAGES TEXTE
        # ---------------------------------------------------------
        if type_msg == "textMessage":
          texte_recu = donnees_message["textMessageData"][
              "textMessage"
          ].strip()
          print(f"\n📩 Message texte reçu de {expediteur} : {texte_recu}")
          texte_cmd = texte_recu.lower()

          if detecter_question_suspecte_ou_systeme(texte_cmd):
            envoyer_reponse_whatsapp(expediteur, MESSAGE_REFUS_SECURITE)
            print("🛡️ Refus de sécurité envoyé.")

          elif texte_cmd in [
              "start",
              "/start",
              "bonjour",
              "salut",
              "hello",
              "menu",
              "aide",
              "hi",
          ]:
            envoyer_reponse_whatsapp(expediteur, MESSAGE_ACCUEIL)
            print("📤 Menu d'accueil envoyé.")

          elif texte_cmd == "1":
            envoyer_reponse_whatsapp(
                expediteur,
                "🔍 *Scanner un message*\n\nTransfère-moi ou colle directement"
                " le texte du message suspect ici.",
            )
          elif texte_cmd == "2":
            envoyer_reponse_whatsapp(
                expediteur,
                "🌐 *Scanner un site / lien*\n\nColle le lien Web (URL) du site"
                " suspect à vérifier.",
            )
          elif texte_cmd == "3":
            envoyer_reponse_whatsapp(expediteur, MESSAGE_SIGNALEMENT_GUIDE)
          elif texte_cmd == "4":
            envoyer_reponse_whatsapp(expediteur, MESSAGE_CONSEILS)

          else:
            analyse = analyser_message(texte_recu)
            reponse_finale = "🛡️ SafeCam V3 - CyberSécurité Cameroun\n\n"
            reponse_finale += f"Verdict : {analyse['verdict']}\n"
            reponse_finale += f"Indice de Risque : {analyse['score_risques']}\n\n"

            if analyse["analyse_detaillee"]:
              reponse_finale += "🔍 Détails de la menace :\n"
              for item in analyse["analyse_detaillee"]:
                reponse_finale += (
                    f"\n📌 {item['type']}\n💡 {item['parade_specifique']}\n"
                )
                for conseil in item["conseils_specifiques"]:
                  reponse_finale += f"• {conseil}\n"
            else:
              reponse_finale += (
                  "Transfère-moi tout message, lien ou offre d'emploi suspect"
                  " pour que je le scanne."
              )

            envoyer_reponse_whatsapp(expediteur, reponse_finale)
            print("📤 Analyse texte envoyée avec succès.")

        # ---------------------------------------------------------
        # TRAITEMENT DES IMAGES / CAPTURES D'ECRAN
        # ---------------------------------------------------------
        elif type_msg in ["imageMessage", "fileMessage"]:
          print(f"\n🖼️ Image reçue de {expediteur}")
          envoyer_reponse_whatsapp(
              expediteur,
              "🔍 *Analyse de l'image en cours...* Patientez un instant pendant"
              " l'inspection du scénario.",
          )

          file_data = donnees_message.get("fileMessageData", {})
          download_url = file_data.get("downloadUrl")

          if download_url:
            fichier_temp = "temp_capture.jpg"
            if télécharger_fichier_greenapi(download_url, fichier_temp):
              # Analyse de la capture d'écran directement via l'API REST Groq
              verdict_image = analyser_image_avec_groq(fichier_temp)
              envoyer_reponse_whatsapp(expediteur, verdict_image)
              print("📤 Analyse d'image envoyée avec succès.")

              # Nettoyage du fichier temporaire
              if os.path.exists(fichier_temp):
                os.remove(fichier_temp)
            else:
              envoyer_reponse_whatsapp(
                  expediteur,
                  "⚠️ Impossible de télécharger l'image reçue. Veuillez"
                  " réessayer.",
              )

      if id_notification:
        session.delete(f"{URL_SUPPRIMER}/{id_notification}")

  except (requests.exceptions.RequestException, Exception) as e:
    time.sleep(2)
