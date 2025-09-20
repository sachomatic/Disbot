from typing import TypedDict
from logging import getLogger
import random


logger = getLogger("game")

#Définition erreurs
ErreurJeu = type("Erreur du jeu", (Exception,), {})
ErreurJoueur = type("Erreur d'un joueur", (ErreurJeu,), {})
ErreurRôle = type("Erreur de rôle", (ErreurJeu,), {})
ErreurJoueurSansRôle = type("Erreur aucun rôle assigné au joueur", (ErreurRôle, ErreurJoueur), {})
ErreurRôleRéassigné = type("Erreur rôle déjà assigné au joueur", (ErreurRôle, ErreurJoueur), {})
ErreurJoueurNonAmoureux = type("Erreur joueur pas amoureux", (ErreurJoueur,), {})
ErreurMauvaiseSélection = type("Erreur mauvaise sélection de joueur", (ErreurJeu,), {})
#Fin définition erreurs


class états:
    INITIALISÉ = 0
    EN_ATTENTE_DE_JOUEURS = 1
    EN_COURS = 2
    ARRÊTÉ = 5


class Cible:
    pass

class Joueur[T](Cible):
    def __init__(self, __objetLié: T, /) -> None:
        self._obj = __objetLié
        self._rôle: Rôle | None = None
        self.mort = False

    @property
    def rôle(self) -> 'Rôle':
        if self.rôle is None:
            raise ErreurJoueurSansRôle(self)
        return self.rôle

    @rôle.setter
    def rôle(self, rôle: 'Rôle', /):
        if not isinstance(rôle, Rôle):
            raise TypeError
        if self._rôle is not None:
            raise ErreurRôleRéassigné(self)
        self._rôle = rôle
        self._rôle.ajouter(self)
    
    def tuer(self):
        pass

    def __del__(self):
        if self._rôle is not None:
            self._rôle.joueurs.remove(self)


def _ajouter(cls, joueur: Joueur, /):
    if not isinstance(joueur, Joueur):
        raise TypeError
    cls.joueurs.add(joueur)
# Créé un type nommé Tous
# dérivé de Cible
# avec pour méthodes et variables
# - `__init__(self) -> None`:  définit l'attribut `joueurs` avec un `set` vide
# - `joueurs: Joueur`: défini comme un `set` par `__init__()`
# - `ajouter(self, joueurs: Joueur, /) -> None`: reflète la fonction `_ajouter` définie ci-dessus
tous = type("Tous", (Cible,), {"__init__": lambda self: setattr(self, "joueurs", set()), "ajouter": _ajouter, "__iter__": lambda self: iter(self.joueurs)})()


class Équipe(Cible):
    def __init__(self, nom: str, /):
        self.nom = nom
        self.joueurs = set["Joueur"]()
    
    def __iter__(self):
        return self.joueurs[:]

    def append(self, joueur: "Joueur"):
        self.joueurs.add(joueur)

class équipes:
    villageois = Équipe("Villageois")
    loups_garous = Équipe("Loups-Garous")
    amoureux = Équipe("Amoureux")


def itérer_cibles(self, *cibles: Cible) -> set[Joueur]:
    retour = set[Joueur]()
    for cible in cibles:
        if cible is tous:
            return set()
        if isinstance(cible, Équipe):
            retour.update(iter(cible))
        elif isinstance(cible, Rôle):
            retour.update(iter(cible))
        elif isinstance(cible, Joueur):
            retour.add(cible)
    for joueur in retour:
        if joueur.mort:
            retour.remove(joueur)
    return retour


class ActionsNuit:
    nom = ""

    def __init__(self):
        super().__init__()
        self.étape = 0
    
    def _check(self, *choix: Joueur):
        for serait_joueur in choix:
                if not isinstance(serait_joueur, Joueur):
                    raise TypeError(serait_joueur)
    
    def agir(self, *choix: Joueur) -> tuple[str, set[Joueur] | None]:
        raise NotImplementedError

class actions_de_nuit:
    class Révéler(ActionsNuit):
        nom = "révéler"

        def __init__(self):
            super().__init__()
            self.restants = set(tous)

        def agir(self, *choix: Joueur) -> tuple[str, set[Joueur] | None]:
            self._check(*choix)
            retour: tuple[str, set[Joueur] | None]
            match self.étape:
                case 0:
                    retour = "La Voyante se réveille, et désigne un joueur dont elle veut sonder la véritable personnalité !", itérer_cibles(tous)
                case 1:
                    retour = "La vraie nature de {9} est " + choix[0].rôle.nom + "\nLa Voyante se rendort", None
                case _:
                    del self
                    raise StopIteration
            self.étape += 1
            return retour

    class Mordre(ActionsNuit):
        nom = "Mordre"

        def __init__(self):
            super().__init__()
        
        def agir(self, *choix: Joueur) -> tuple[str, set[Joueur] | None]:
            self._check(*choix)
            retour: tuple[str, set[Joueur] | None]
            match self.étape:
                case 0:
                    retour= "Les Loups-Garous se réveillent, se reconnaissent et désignent une nouvelle victime !!!", itérer_cibles(équipes.villageois)
                case 1:
                    if len(choix) != 1:
                        raise ErreurMauvaiseSélection
                    retour = "Les Loups-Garous repus se rendorment et rêvent de prochaines victimes savoureuses !", None
                case _:
                    del self
                    raise StopIteration
            self.étape += 1
            return retour
            
class Rôle:
    def __init__(
        self, nom: str, description: str, équipe: Équipe, *capacités: ActionsNuit
    ) -> None:
        self.nom = nom
        self.description = description
        self.équipe = équipe
        self.capacités = capacités
        self.joueurs = set["Joueur"]()
    
    def __iter__(self):
        return self.joueurs[:]

    def ajouter(self, joueur: "Joueur"):
        self.joueurs.add(joueur)


class rôles:
    villageois = Rôle(
        "Villageois",
        "Il n’a aucune compétence particulière. Ses seules armes sont la capacité d’analyse des comportements pour identifier les Loups-Garous, et la force de conviction pour empêcher l’exécution de l’innocent qu’il est.",
        équipes.villageois,
    )
    voyante = Rôle(
        "Voyante",
        "Chaque nuit, elle découvre la vraie personnalité d’un joueur de son choix. Elle doit aider les autres Villageois, mais rester discrète pour ne pas être démasquée par les Loups-Garous.",
        équipes.villageois,
        None,
    )
    chasseur = Rôle("Chasseur", "S’il se fait dévorer par les Loups-Garous ou exécuter malencontreusement par les joueurs, le Chasseur doit répliquer avant de rendre l’âme, en éliminant immédiatement n’importe quel autre joueur de son choix.", équipes.villageois)
    cupidon = Rôle("Cupidon", "", équipes.villageois, None)
    sorcière = Rôle("Sorcière", "", équipes.villageois, None)
    petite_fille = Rôle(
        "Petite fille", "", équipes.villageois
    )  # inutilisable sur Discord
    voleur = Rôle("Voleur", "", équipes.villageois, None)
    loup_garou = Rôle("Loup-Garou", "", équipes.loups_garous, None)


class Amoureux:
    def __init__(self, joueur1: Joueur, joueur2: Joueur, /):
        self.joueur1, self.joueur2 = joueur1, joueur2

    def other(self, joueur):
        match joueur:
            case self.joueur1:
                return self.joueur2
            case self.joueur2:
                return self.joueur1
            case _:
                raise ErreurJoueurNonAmoureux


class variantes_type(TypedDict):
    min: int
    max: int
    rôles: dict[Rôle, dict[int, int]]
    ordre: list[type[ActionsNuit]]


variantes_disponibles: dict[str, variantes_type] = {
    "défaut": {
        "min": 8,
        "max": 18,
        "rôles": {
            rôles.loup_garou: {
                **{i: 2 for i in range(8, 12)},
                **{i: 3 for i in range(12, 19)},
            },
            rôles.voyante: {i: 1 for i in range(8, 19)},
            rôles.chasseur: {i: 1 for i in range(8, 19)},
            rôles.cupidon: {i: 1 for i in range(8, 19)},
            rôles.sorcière: {i: 1 for i in range(8, 19)},
            rôles.voleur: {i: 1 for i in range(8, 19)},
            rôles.villageois: {i: i - 7 for i in range(8, 19)},
        },
        "ordre": [
            actions_de_nuit.Mordre
        ],
    }
}


class Jeu[TObjLiéAuxJoueurs]:
    def __init__(self) -> None:
        self.état = états.INITIALISÉ
        self.joueurs = dict[TObjLiéAuxJoueurs, Joueur[TObjLiéAuxJoueurs]]()
        logger.debug("Jeu créé")

    def choisir_variante(self, nom_variante: str, /):
        if self.état is not états.INITIALISÉ:
            return 2
        if nom_variante not in variantes_disponibles:
            return 1
        self.variante_choisie = variantes_disponibles[nom_variante]
        self.état = états.EN_ATTENTE_DE_JOUEURS
        return 0

    def ajouter_un_joueur(self, __objet_lié: TObjLiéAuxJoueurs, /) -> int:
        if self.état is not états.EN_ATTENTE_DE_JOUEURS:
            return 1
        if __objet_lié in self.joueurs.keys():
            return 2
        if len(self.joueurs) > self.variante_choisie["max"]:
            return 3
        self.joueurs[__objet_lié] = Joueur(__objet_lié)
        return 0

    def assigner_rôles(self) -> int:
        if self.état is not états.EN_ATTENTE_DE_JOUEURS:
            return 1
        nb_joueurs = len(self.joueurs)
        if (
            nb_joueurs < self.variante_choisie["min"]
            or nb_joueurs > self.variante_choisie["max"]
        ):
            return 2

        rôles_config = self.variante_choisie["rôles"]
        rôles_à_assigner = []
        for rôle, config in rôles_config.items():
            n = config.get(nb_joueurs, 0)
            rôles_à_assigner.extend([rôle] * n)

        random.shuffle(rôles_à_assigner)

        for joueur, rôle in zip(self.joueurs.values(), rôles_à_assigner):
            joueur.rôle = rôle

        self.état = états.EN_COURS

        return 0

    def stop(self) -> int:
        if self.état is états.INITIALISÉ:
            return 1
        return 0

    def __del__(self):
        self.stop()
        for joueur in self.joueurs.values():
            del joueur


if __name__ == "__main__":
    jeu = Jeu[int]()
    assert jeu.choisir_variante("défaut") == 0
    for j in range(1, 19):
        assert jeu.ajouter_un_joueur(j) == 0
    assert jeu.assigner_rôles() == 0
    for j in jeu.joueurs.values():
        print(j.rôle.nom)
