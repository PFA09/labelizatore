# 🎙️ Labelizatore - Annotation Audio

Labelizatore est un outil interne développé avec Python et Streamlit pour faciliter le nettoyage, le découpage et l'annotation de fichiers audio longs (contenant notamment des données de voix pathologiques). 

L'outil automatise le découpage par silence, permet de scinder/fusionner les erreurs, et attribue des labels à la volée tout en sauvegardant l'avancement dans un fichier `labels.json`.

---

## 🛠️ Installation & Démarrage

### 1. Prérequis Systèmes
L'outil utilise `Pydub` pour le découpage de l'audio. Pydub a besoin du programme `ffmpeg` pour fonctionner correctement. 
Sous Linux (Ubuntu/Debian) :
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Installations des dépendances Python
Rendez-vous dans le dossier du projet, et installez les librairies requises :
```bash
pip install streamlit pydub
```

### 3. Lancer l'application
Exécutez l'application en lançant la commande suivante dans le terminal :
```bash
streamlit run app.py
```
*Votre navigateur s'ouvrira automatiquement à l'adresse `http://localhost:8501`.*

---

## 📖 Guide d'utilisation Étape par Étape

### 📝 Étape 1 : Paramétrage & Métadonnées
Au lancement, choisissez les informations liées à l'enregistrement en cours pour que l'outil remplisse automatiquement les dictionnaires correspondants.
1. Sélectionnez une **Session**, **Speaker**, ou **Micro** existant dans les listes déroulantes (générées depuis vos précédentes annotations dans `labels.json`).
2. S'il s'agit d'un nouveau locuteur ou d'une nouvelle session, remplissez les champs *"Ou nouveau..."* situés juste en dessous.

### 📝 Étape 2 : Préparation de la File de Labels Attendus
L'une des forces de l'outil est d'anticiper le flux de travail. Vous savez généralement quelle est la suite de mots ou lettres que le locuteur a tenté de prononcer.
1. Allez dans la section **Composition de la file d'attente**.
2. Tapez la séquence attendue dans le champ *"Taper une séquence"*.
3. Choisissez l'une des trois méthodes :
   - **➕ Ajouter entier [Entrée]** : Ajoute la phrase complète (sans coupures) comme étant le label numéro 1.
   - **✂️ Scinder en mots** : Si vous tapez `Bonjour tout le monde`, l'outil ajoutera un bloc par mot (*"Bonjour"*, puis *"tout"*, puis *"le"*...).
   - **✂️ Scinder en lettres** : Si le locuteur épelait, tapez les lettres, scindez-les, et l'outil les séparera une par une (en isolant même les espaces/caractères spéciaux).
4. Le tableau dynamique s'affiche. *Astuce : Vous pouvez cliquer à l'intérieur du tableau pour éditer une faute de frappe, ou cocher une case à gauche pour supprimer une ligne avant de passer à la suite.*

### ✂️ Étape 3 : Import et Découpage Audio Source
1. Glissez-déposez votre enregistrement long (format `.wav`) dans la zone dédiée.
2. Ajustez les "Sliders" de silence (par exemple, baissez à 100ms si le locuteur parle haché ou sans pauses marquées).
3. Cliquez sur **🚀 Lancer le découpage de l'audio.** L'outil va localiser les silences et créer un petit fichier `.wav` par mot/lettre trouvée.

### 🎧 Étape 4 : Le Flux d'Étiquetage Actif (Workflow Itératif)
Félicitations, vos audios sont découpés ! L'interface bascule en mode lecteur avec raccourcis. Dès qu'un segment apparaît, l'audio se joue automatiquement. Vous avez alors plusieurs choix visuels ou par raccourcis clavier :

#### **L'audio comporte une erreur de découpage :**
*   **[S] ✂️ Scinder :** L'audio contient deux mots ("Bonjour tout"). Inscrivez la milliseconde de coupure (ex: `1000`) dans Timecode et scindez. L'audio sera coupé en deux, modifiant l'extrait actuel, et insérant la suite immédiatement à la prochaine étape.
*   **[F] ➕ Fusionner :** L'audio est coupé au milieu d'un mot ("Bon..."). Fusionnez avec le suivant.
*   **[Suppr] 🗑️ Rejeter :** C'était un bruit de chaise ou un souffle ? Supprimez-le du flux. Le label attendu *n'est pas consommé* et vous passerez au vrai mot suivant.

#### **L'audio correspond au texte attendu :**
La liste de boutons s'affiche sous le lecteur avec les labels que vous avez préparés à l'Étape 2.
*   Le bouton **rouge (avec la cible 🎯)** tout en haut est le label séquentiellement attendu d'après votre file d'attente (Raccourci **[1]**).
*   Cliquez dessus (ou appuyez sur **1**) :
    - L'audio sera labellisé.
    - Il est enregistré sur votre disque local sous le dossier `labeled_data/`.
    - Le `labels.json` enregistrera votre méta-donnée, le nom du fichier, et son *Type* déduit automatiquement (Lettre, Mot, Phrase...).
    - L'extrait suivant se lancera.

#### **L'audio correspond mais a été mal prononcé / n'était pas dans la liste :**
Si le locuteur a sauté un mot, dit autre chose, ou qu'il prononce un mot ne figurant pas dans la file d'attente :
* Allez dans le premier sous-menu **"Validation : Saisie manuelle"**.
* Tapez le mot tel qu'il a été dit.
* Appuyez sur **[Entrée]**. 
Ce mode valide l'audio manuellement et **ne supprime aucun élément** de votre liste de labels préparée pour la suite du flux.

---

*L'opération s'interrompt d'elle-même quand tous les extraits tirés du `.wav` initial ont été traités.*

