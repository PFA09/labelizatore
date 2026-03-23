import streamlit as st
import streamlit.components.v1 as components
import json
import os
import shutil
import time
import uuid
from pydub import AudioSegment
from pydub.silence import split_on_silence

# --- Configuration des chemins ---
LABELS_FILE = "labels.json"
OUTPUT_DIR = "labeled_data"
TEMP_DIR = "temp_chunks"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --- Fonctions utilitaires ---
def load_labels():
    if not os.path.exists(LABELS_FILE):
        return []
    try:
        with open(LABELS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except json.JSONDecodeError:
        return []

def save_label(new_entry):
    labels = load_labels()
    labels.append(new_entry)
    with open(LABELS_FILE, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=4, ensure_ascii=False)

def get_unique_values(key, labels):
    return list(set(item.get(key, "") for item in labels if item.get(key)))

def deduce_type(label):
    if len(label) == 1:
        if label.isalpha():
            return "Letter"
        if label.isdigit():
            return "Digit"
        return "Special"
    else:
        if " " in label.strip():
            return "Sentence"
        return "Word"

def register_labeled_audio(chunk_path, raw_label):
    if not os.path.exists(chunk_path):
        st.error(f"Erreur : Le fichier source {chunk_path} n'existe plus ou est inaccessible.")
        return False

    clean_label = raw_label.strip()
    computed_type = deduce_type(clean_label)
    
    final_filename = f"{st.session_state.meta_speaker}_{st.session_state.meta_session}_{int(time.time() * 1000)}.wav"
    final_path = os.path.join(OUTPUT_DIR, final_filename)
    
    try:
        shutil.copy(chunk_path, final_path)
    except Exception as e:
        st.error(f"Erreur lors de la copie du fichier : {e}")
        return False
    
    new_entry = {
        "file": final_filename,
        "label": clean_label,
        "type": computed_type,
        "speaker": st.session_state.meta_speaker,
        "micro": st.session_state.meta_micro,
        "session": st.session_state.meta_session
    }
    
    try:
        save_label(new_entry)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du label : {e}")
        return False

# --- Initialisation de l'état (Session State) ---
if "step" not in st.session_state:
    st.session_state.step = "config"
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "current_chunk_idx" not in st.session_state:
    st.session_state.current_chunk_idx = 0
if "expected_labels" not in st.session_state:
    st.session_state.expected_labels = []

labels_data = load_labels()

# ==========================================
# INJECTION JS POUR RACCOURCIS CLAVIER
# ==========================================
js_hotkeys = """
<script>
const doc = window.parent.document;
if (!doc.getElementById('labelizatore-hotkeys')) {
    const script = doc.createElement('script');
    script.id = 'labelizatore-hotkeys';
    script.innerHTML = `
        document.addEventListener('keydown', function(e) {
            // Ne pas écouter si l'utilisateur tape dans un champ de texte
            if (['INPUT', 'TEXTAREA'].includes(e.target.nodeName)) return;

            const buttons = Array.from(document.querySelectorAll('button'));
            const clickBtn = (textPart) => {
                const btn = buttons.find(b => b.innerText.includes(textPart));
                if(btn) btn.click();
            };

            if (e.key === 'Delete') {
                clickBtn('[Suppr]');
            } else if (e.key.toLowerCase() === 'f') {
                clickBtn('[F]');
            } else if (e.key.toLowerCase() === 's') {
                clickBtn('[S]');
            } else if (e.key === ' ' || e.code === 'Space') {
                // Intercepter l'espace pour Play/Pause l'audio
                const audio = document.querySelector('audio');
                if(audio) {
                    e.preventDefault(); // Empêcher la page de descendre
                    audio.paused ? audio.play() : audio.pause();
                }
            } else if (/^[1-9]$/.test(e.key)) {
                // Chiffres de 1 à 9
                clickBtn('[' + e.key + ']');
            }
        });
    `;
    doc.head.appendChild(script);
}
</script>
"""
components.html(js_hotkeys, height=0, width=0)


st.title("🎙️ Labelizatore - Annotation Audio")

# ==========================================
# ETAPE 1 & 2 : Configuration & Découpage
# ==========================================
if st.session_state.step in ["config", "split"]:
    st.header("1. Paramétrage & Découpage")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Métadonnées")
        sessions = get_unique_values("session", labels_data)
        sel_session = st.selectbox("Session existante", [""] + sessions)
        new_session = st.text_input("Ou nouvelle session")
        final_session = new_session if new_session else sel_session
        
        speakers = get_unique_values("speaker", labels_data)
        sel_speaker = st.selectbox("Speaker existant", [""] + speakers)
        new_speaker = st.text_input("Ou nouveau speaker")
        final_speaker = new_speaker if new_speaker else sel_speaker

    with col2:
        st.subheader(" .")
        micros = get_unique_values("micro", labels_data)
        sel_micro = st.selectbox("Micro existant", [""] + micros)
        new_micro = st.text_input("Ou nouveau micro")
        final_micro = new_micro if new_micro else sel_micro

    # --- File d'attente des labels (Édition dynamique) ---
    st.divider()
    st.subheader("Composition de la file d'attente")
    
    st.markdown("💡 **Ajout de séquence**")
    with st.form("queue_add_form", clear_on_submit=True):
        quick_seq = st.text_input("Taper une séquence :", placeholder="ex: ça va bien, ou a b c")
        c1, c2, c3 = st.columns(3)
        add_full = c1.form_submit_button("➕ Ajouter entier [Entrée]", use_container_width=True)
        split_words = c2.form_submit_button("✂️ Scinder en mots", use_container_width=True)
        split_chars = c3.form_submit_button("✂️ Scinder en lettres", use_container_width=True)
        
        if add_full and quick_seq.strip():
            st.session_state.expected_labels.append(quick_seq.strip())
            st.rerun()
        elif split_words and quick_seq.strip():
            words = [w for w in quick_seq.split(" ") if w.strip()]
            st.session_state.expected_labels.extend(words)
            st.rerun()
        elif split_chars and quick_seq:
            chars = list(quick_seq)
            st.session_state.expected_labels.extend(chars)
            st.rerun()

    st.markdown("📝 **Visualisation et Édition manuelle** (modifiez les textes ou ajoutez/supprimez des lignes)")
    if len(st.session_state.expected_labels) > 0:
        # Transformation en liste de dictionnaires pour Data Editor native (pas besoin de pandas)
        table_data = [{"Label": lbl} for lbl in st.session_state.expected_labels]
        edited_table = st.data_editor(table_data, num_rows="dynamic", use_container_width=True)
        
        # Mettre à jour l'état seulement sans recharger en boucle
        updated_labels = [row["Label"] for row in edited_table if row.get("Label")]
        st.session_state.expected_labels = updated_labels
        
        if st.button("🗑️ Vider la file"):
            st.session_state.expected_labels = []
            st.rerun()
    else:
        st.info("La file est vide. Utilisez la saisie ci-dessus pour la remplir.")

    # --- Traitement Audio ---
    st.divider()
    st.subheader("Traitement Audio Source")
    uploaded_file = st.file_uploader("Importer un fichier audio long (.wav)", type=["wav"])
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        min_silence = st.slider(
            "Longueur min du silence (ms)", 
            min_value=50, max_value=2000, value=150, step=10
        )
    with col_s2:
        silence_thresh = st.slider(
            "Seuil de silence (dBFS)", 
            min_value=-80, max_value=-10, value=-40, step=1
        )

    if st.button("🚀 Lancer le découpage de l'audio", type="primary"):
        if uploaded_file is None:
            st.error("Veuillez uploader un fichier audio.")
        elif not final_session or not final_speaker:
            st.warning("Veuillez remplir au moins la Session et le Speaker.")
        else:
            if os.path.exists(TEMP_DIR):
                shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR, exist_ok=True)
            
            with st.spinner("Découpage en cours..."):
                temp_path = os.path.join(TEMP_DIR, "source.wav")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                audio = AudioSegment.from_wav(temp_path)
                chunks = split_on_silence(
                    audio,
                    min_silence_len=min_silence,
                    silence_thresh=silence_thresh,
                    keep_silence=100
                )
                
                chunk_paths = []
                for i, chunk in enumerate(chunks):
                    c_path = os.path.join(TEMP_DIR, f"chunk_{i}.wav")
                    chunk.export(c_path, format="wav")
                    chunk_paths.append(c_path)
                
                if not chunk_paths:
                    st.error("Aucun découpage trouvé ! Ajustez les sliders de silence.")
                else:
                    st.success(f"{len(chunk_paths)} sous-fichiers générés !")
                    st.session_state.chunks = chunk_paths
                    st.session_state.current_chunk_idx = 0
                    
                    st.session_state.meta_session = final_session
                    st.session_state.meta_speaker = final_speaker
                    st.session_state.meta_micro = final_micro
                    
                    st.session_state.step = "label"
                    st.rerun()


# ==========================================
# ETAPE 3 : Interface d'Etiquetage
# ==========================================
elif st.session_state.step == "label":
    st.header("3. Étiquetage itératif")
    
    idx = st.session_state.current_chunk_idx
    chunks = st.session_state.chunks
    
    if idx >= len(chunks):
        st.success("Toutes les parties de ce fichier ont été traitées ! 🎉")
        if st.button("Traiter un nouveau fichier"):
            st.session_state.step = "config"
            st.rerun()
    else:
        current_chunk_path = chunks[idx]
        
        # Astuce Raccourcis visuels
        st.markdown("*Raccourcis : **[Espace]** (Play/Pause) — **[Entrée]** (Sauvegarder Saisie Manuelle) — **[F]** (Fusionner) — **[S]** (Scinder) — **[Suppr]** (Rejeter) — **[1...9]** (Labels)*")
        
        st.progress((idx) / len(chunks))
        st.write(f"**Extrait {idx + 1} / {len(chunks)}**")
        
        # --- LECTEUR AUDIO ---
        audio_error = False
        try:
            if not os.path.exists(current_chunk_path):
                raise FileNotFoundError("Fichier introuvable sur le disque.")
            
            # Lecture automatique (autoplay) via composant HTML
            st.audio(current_chunk_path, format="audio/wav")
            # import base64
            # with open(current_chunk_path, "rb") as f:
            #     data = f.read()
            #     b64 = base64.b64encode(data).decode()
            #     md = f"""
            #         <audio id="autoAudio" controls autoplay style="width:100%;">
            #         <source src="data:audio/wav;base64,{b64}" type="audio/wav">
            #         Votre navigateur ne supporte pas la balise audio.
            #         </audio>
            #         """
            #     st.markdown(md, unsafe_allow_html=True)
                
        except Exception as e:
            audio_error = True
            st.error(f"⚠️ Impossible de lire l'audio : {e}")
            if st.button("⏭️ Fichier corrompu - Passer au suivant", use_container_width=True):
                st.session_state.current_chunk_idx += 1
                st.rerun()
        
        # --- OUTILS DE CORRECTION AUDIO ---
        # Sorti de l'expander pour que les raccourcis JS soient sûrs de trouver les boutons
        st.markdown("### 🛠️ Outils de correction audio")
        col_merge, col_split1, col_split2 = st.columns([1.2, 1, 1])
        with col_merge:
            if idx < len(chunks) - 1:
                if st.button("➕ Fusionner avec le suivant [F]"):
                    try:
                        audio1 = AudioSegment.from_wav(current_chunk_path)
                        audio2 = AudioSegment.from_wav(chunks[idx + 1])
                        merged_audio = audio1 + audio2
                        
                        merged_audio.export(current_chunk_path, format="wav")
                        try:
                            os.remove(chunks[idx + 1])
                        except: 
                            pass
                        
                        st.session_state.chunks.pop(idx + 1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur fusion : {e}")
            else:
                st.info("Dernier extrait.")
                
        with col_split1:
            split_time = st.number_input("Timecode (ms)", min_value=0, value=0, step=100)
            
        with col_split2:
            st.write("") 
            if st.button("✂️ Scinder l'audio [S]"):
                if split_time > 0:
                    try:
                        audio = AudioSegment.from_wav(current_chunk_path)
                        if split_time < len(audio):
                            part1 = audio[:split_time]
                            part2 = audio[split_time:]
                            
                            part1.export(current_chunk_path, format="wav")
                            
                            part2_path = os.path.join(TEMP_DIR, f"chunk_{idx}_split_{uuid.uuid4().hex[:6]}.wav")
                            part2.export(part2_path, format="wav")
                            
                            st.session_state.chunks.insert(idx + 1, part2_path)
                            st.rerun()
                        else:
                            st.warning("Timecode trop grand.")
                    except Exception as e:
                        st.error(f"Erreur scission : {e}")
                else:
                    st.warning("Temps invalide.")

        st.markdown("---")
        st.subheader("Validation")

        # --- OPTION A : SAISIE MANUELLE ---
        with st.form(key="manual_label_form", clear_on_submit=True):
            user_label = st.text_input("Saisie manuelle :", placeholder="Label hors-file")
            col_a, col_b = st.columns(2)
            # En HTML classique, soummettre un form dans un text input se fait avec la touche "Entrée" naturellement !
            submit_manual = col_a.form_submit_button("✅ Enregistrer la saisie [Entrée]", use_container_width=True)
            submit_reject = col_b.form_submit_button("🗑️ Rejeter l'audio (bruit) [Suppr]", use_container_width=True)
            
        if submit_manual:
            if not user_label.strip():
                st.error("Le label ne peut pas être vide.")
            else:
                success = register_labeled_audio(current_chunk_path, user_label)
                if success:
                    st.session_state.current_chunk_idx += 1
                    st.rerun()
                
        if submit_reject:
            try:
                os.remove(current_chunk_path)
            except:
                pass
            st.session_state.current_chunk_idx += 1
            st.rerun()

        # --- OPTION B : SELECTION RAPIDE DANS LA FILE ---
        if st.session_state.expected_labels:
            st.markdown("### Ou sélectionner depuis la file d'attente :")
            
            for i, queued_label in enumerate(st.session_state.expected_labels):
                
                # Attribuer les raccourcis "1" à "9" pour les premiers éléments visuellement
                shortcut = f" [{i+1}]" if i < 9 else ""
                emoji = "🎯 " if i == 0 else ""
                btn_type = "primary" if i == 0 else "secondary"
                
                btn_label = f"{emoji}{queued_label}{shortcut}"
                
                # Le format unique previent les confits de clés
                if st.button(btn_label, key=f"btn_queue_{i}_{queued_label}", use_container_width=True, type=btn_type):
                    success = register_labeled_audio(current_chunk_path, queued_label)
                    if success:
                        st.session_state.expected_labels.pop(i)
                        st.session_state.current_chunk_idx += 1
                        st.rerun()
