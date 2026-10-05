import re
import unicodedata
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# CONSTANTES MÉTIER
# ---------------------------------------------------------
CORRESPONDANCES = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'O': 6, 'P': 7, 'Q': 8, 'R': 9,
    'S': 1, 'T': 2, 'U': 3, 'V': 4, 'W': 5, 'X': 6, 'Y': 7, 'Z': 8
}

VOYELLES = "AEIOUY"

# ---------------------------------------------------------
# SCHÉMAS PYDANTIC (Validation & Documentation Swagger)
# ---------------------------------------------------------
class TableInclusion(BaseModel):
    grille: Dict[int, int]
    manquants: List[int]
    dominants: List[int]
    total_lettres: int

class ProfilNumerologiqueResponse(BaseModel):
    identite_source: str
    nb_mots: int
    expression: int = Field(..., description="Nombre d'Expression (Total)")
    calcul_expression: str
    elan_spirituel: int = Field(..., description="Ame / Elan spirituel (Voyelles)")
    calcul_elan: str
    moi_intime: int = Field(..., description="Personnalité / Moi intime (Consonnes)")
    calcul_moi: str
    table_inclusion: TableInclusion

class AnalyseRequest(BaseModel):
    identite: str = Field(..., min_length=1, max_length=150, example="Jean-Luc Dupont")

# ---------------------------------------------------------
# FONCTIONS MÉTIER
# ---------------------------------------------------------
def supprimer_accents(texte: str) -> str:
    """Normalise le texte pour transformer é, è, ê en E, ç en C, etc."""
    nfkd = unicodedata.normalize('NFKD', texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def reduire_nombre(nombre: int) -> int:
    """Réduit un nombre selon les règles numérologiques en préservant 11, 22 et 33."""
    while nombre > 9:
        if nombre in [11, 22, 33]:
            break
        nombre = sum(int(chiffre) for chiffre in str(nombre))
    return nombre

def formater_reduction(valeur_initiale: int) -> str:
    """Génère la chaîne textuelle montrant les étapes successives de réduction."""
    etapes = [valeur_initiale]
    courant = valeur_initiale
    while courant > 9:
        if courant in [11, 22, 33]:
            break
        courant = sum(int(c) for c in str(courant))
        etapes.append(courant)

    if len(etapes) == 1:
        return str(etapes[0])
    return " -> ".join(map(str, etapes))

def valider_identite(identite_complete: str) -> Optional[List[str]]:
    """Nettoie, gère les accents, tirets, espaces et ne retient que l'alphabet A-Z."""
    if not identite_complete or not isinstance(identite_complete, str):
        return None

    texte_propre = supprimer_accents(identite_complete)
    mots_bruts = re.split(r'[\s\-]+', texte_propre.strip())
    mots_valides = [''.join(c for c in mot.upper() if c.isalpha()) for mot in mots_bruts]
    mots_valides = [m for m in mots_valides if len(m) > 0]

    return mots_valides if mots_valides else None

def analyser_mot(mot_nettoye: str) -> dict:
    somme_voyelles = sum(CORRESPONDANCES[l] for l in mot_nettoye if l in VOYELLES)
    somme_consonnes = sum(CORRESPONDANCES[l] for l in mot_nettoye if l not in VOYELLES)
    return {
        "mot": mot_nettoye,
        "voyelles_brut": somme_voyelles,
        "consonnes_brut": somme_consonnes,
        "total_brut": somme_voyelles + somme_consonnes,
    }

def calculer_table_inclusion(mots: List[str]) -> dict:
    grille = {chiffre: 0 for chiffre in range(1, 10)}
    total_lettres = 0

    for mot in mots:
        for lettre in mot:
            valeur = CORRESPONDANCES[lettre]
            grille[valeur] += 1
            total_lettres += 1

    manquants = [chiffre for chiffre, compte in grille.items() if compte == 0]
    dominants = [chiffre for chiffre, compte in grille.items() if compte >= 3]

    return {
        "grille": grille,
        "manquants": manquants,
        "dominants": dominants,
        "total_lettres": total_lettres
    }

def construire_profil(identite_complete: str) -> Optional[dict]:
    mots = valider_identite(identite_complete)
    if not mots:
        return None

    analyses = [analyser_mot(m) for m in mots]
    nb_mots = len(analyses)

    total_voyelles_brut = sum(a["voyelles_brut"] for a in analyses)
    total_consonnes_brut = sum(a["consonnes_brut"] for a in analyses)
    total_general_brut = sum(a["total_brut"] for a in analyses)

    elan_spirituel = reduire_nombre(total_voyelles_brut)
    moi_intime = reduire_nombre(total_consonnes_brut)
    expression = reduire_nombre(total_general_brut)

    details_voyelles = [f"{a['mot']} ({a['voyelles_brut']})" for a in analyses]
    details_consonnes = [f"{a['mot']} ({a['consonnes_brut']})" for a in analyses]
    details_total = [f"{a['mot']} ({a['total_brut']})" for a in analyses]

    if nb_mots == 1:
        calc_elan = f"{details_voyelles[0]} = {formater_reduction(total_voyelles_brut)}"
        calc_moi = f"{details_consonnes[0]} = {formater_reduction(total_consonnes_brut)}"
        calc_exp = f"{details_total[0]} = {formater_reduction(total_general_brut)}"
    else:
        calc_elan = f"{' + '.join(details_voyelles)} => {total_voyelles_brut} = {formater_reduction(total_voyelles_brut)}"
        calc_moi = f"{' + '.join(details_consonnes)} => {total_consonnes_brut} = {formater_reduction(total_consonnes_brut)}"
        calc_exp = f"{' + '.join(details_total)} => {total_general_brut} = {formater_reduction(total_general_brut)}"

    return {
        "identite_source": identite_complete.strip(),
        "nb_mots": nb_mots,
        "expression": expression,
        "calcul_expression": calc_exp,
        "elan_spirituel": elan_spirituel,
        "calcul_elan": calc_elan,
        "moi_intime": moi_intime,
        "calcul_moi": calc_moi,
        "table_inclusion": calculer_table_inclusion(mots)
    }

# ---------------------------------------------------------
# APPLICATION FASTAPI & ROUTES
# ---------------------------------------------------------
app = FastAPI(
    title="Numerology API",
    description="API de calcul numérologique standard (Expression, Ame, Personnalité et Table d'Inclusion).",
    version="1.0.0"
)

# Autorise Framer et les requêtes externes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Healthcheck"])
def root():
    return {"status": "ok", "message": "Numerology API en ligne"}

@app.get("/api/numerologie", response_model=ProfilNumerologiqueResponse, tags=["Numerologie"])
def get_numerologie(identite: str = Query(..., min_length=1, max_length=150, description="Nom et prénom(s)")):
    """Calcul via requête GET (idéal pour tester directement dans le navigateur ou fetch simple)."""
    profil = construire_profil(identite)
    if not profil:
        raise HTTPException(
            status_code=400,
            detail="Aucune lettre valide trouvée dans l'identité fournie."
        )
    return profil

@app.post("/api/numerologie", response_model=ProfilNumerologiqueResponse, tags=["Numerologie"])
def post_numerologie(payload: AnalyseRequest):
    """Calcul via requête POST avec corps JSON."""
    profil = construire_profil(payload.identite)
    if not profil:
        raise HTTPException(
            status_code=400,
            detail="Aucune lettre valide trouvée dans l'identité fournie."
        )
    return profil
