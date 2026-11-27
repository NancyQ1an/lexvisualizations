"""
Builds multilingual_tree_data.csv: a real-data transcription of Pokorny's
entry for the PIE root *ar- ("to fit together") and its extensions. This is
the project's working dataset (replacing the earlier hand-built synthetic
demo, preserved in git history) - same column shape as before
(id, word, parent_id, meaning, category, tags, paradigm_id) plus one new
`is_doubtful` column.

Scope decisions made explicitly (not silently):
- Glosses are kept in German, as printed by Pokorny - translating ~200
  archaic/technical glosses risks introducing more error than it fixes.
- The six group labels in the source (t-Bildungen; two m-Bildungen groups;
  Wzf. re-/ra- [+dh-Erweiterung]; Wzf. (a)ri-/rei- [+dh-Erweiterung]) become
  sub-root nodes under a new AR_ROOT (*ar-), each via parent_id.
- Rows Pokorny himself marks doubtful ([CHECK] in the source notes, or
  described as allegedly/vermutlich/vielleicht belonging here) get
  is_doubtful=True rather than being silently included or excluded.
- Explicit "equated (=) with" cross-linguistic cognate pairs are linked via
  paradigm_id (reusing the suppletion-paradigm mechanism for genuine
  synchronic cognate pairs, not just suppletion).
- NOT preserved in this pass: the bibliographic citations (Bugge KZ. 32, 21,
  etc.) and most footnote commentary - this schema has no column for them.
  A real follow-up would feed these into the citations/sources mechanism
  already built for the toy dataset.
- This is a first-pass transcription of a large, intricate real dictionary
  entry - worth spot-checking against the source, not treated as
  error-free simply because it's sourced from real data.
"""

import csv

rows = []
seen_ids = set()


def add(id_, word, parent_id, meaning, category, tags, paradigm_id="", is_doubtful=False):
    if id_ in seen_ids:
        raise ValueError(f"duplicate id: {id_}")
    seen_ids.add(id_)
    rows.append({
        "id": id_, "word": word, "parent_id": parent_id, "meaning": meaning,
        "category": category, "tags": tags, "paradigm_id": paradigm_id,
        "is_doubtful": "TRUE" if is_doubtful else "",
    })


PHYS = "Physical Acts"
BODY = "Body"

# --- Root ---
add("AR_ROOT", "*ar-", "", "zusammenfügen, passen", "", "PIE-root")

# --- Base-grade reflexes (no group label in source = direct children of the root) ---
add("ARM_ERI", "eri", "AR_ROOT", "Bug, Schulter von Tieren", PHYS, "Armenian", is_doubtful=True)
add("AV_ARANTE", "arānte", "AR_ROOT", "sie setzen sich fest, bleiben stecken", PHYS, "Avestan")
add("AI_ARAH", "ará-ḥ", "AR_ROOT", "Radspeiche", PHYS, "Sanskrit")
add("AI_ARAM", "aram / álam", "AR_ROOT", "passend, genug", PHYS, "Sanskrit")
add("AI_ARAMKAR", "áraṃkar- / alaṃkar", "AI_ARAM", "zurechtmachen und dienen", PHYS, "Sanskrit")
add("AI_ARATI", "ara-tí-", "AI_ARAMKAR", "Diener", PHYS, "Sanskrit")
add("AI_RATI", "rā-tí-", "AI_ARAMKAR", "bereitwillig", PHYS, "Sanskrit")
add("AV_RAITI", "rāiti", "AI_ARAMKAR", "dienstwillig, Diener", PHYS, "Avestan")
add("AV_AREM", "arəm", "AR_ROOT", "passend, entsprechend", PHYS, "Avestan")
add("AV_AREMPITHWA", "arə̄m-piϑwā", "AV_AREM", "Mittag", PHYS, "Avestan")
add("AV_RAPITHWA", "ra-piϑwā", "AV_AREM", "Mittag", PHYS, "Avestan")
add("AV_RATU", "ratu-", "AR_ROOT", "Richter, Schiedsrichter und Zeitraum", PHYS, "Avestan")
add("AI_ARPAYATI", "ar-p-áyati", "AR_ROOT", "steckt hinein, befestigt", PHYS, "Sanskrit")
add("HETT_HARAP", "ḫar-ap- / ḫarp-", "AR_ROOT", "hinstellen", PHYS, "Hittite", is_doubtful=True)
add("ARM_ARNEM", "aṙnem", "AR_ROOT", "mache", PHYS, "Armenian")
add("ARM_YAR", "y-ar", "AR_ROOT", "consentaneo, congiunto, contiguo, appresso", PHYS, "Armenian")
add("ARM_ARAR", "arar", "AR_ROOT", "hat gemacht", PHYS, "Armenian", paradigm_id="PARA_ARAR_ARARE")
add("GR_ARARE", "ἄραρε", "AR_ROOT", "hat gemacht", PHYS, "Greek", paradigm_id="PARA_ARAR_ARARE")
add("ARM_YAREM", "yarem", "ARM_YAR", "aggiungere, congiungere", PHYS, "Armenian")
add("ARM_CCAR", "č̣ar", "AR_ROOT", "schlecht", PHYS, "Armenian")
add("GR_ARARISKO", "ἀραρίσκω", "AR_ROOT", "füge zusammen", PHYS, "Greek")
add("GR_ARMENOS", "ἄρμενος", "AR_ROOT", "angefügt, passend", PHYS, "Greek")
add("GR_OAR", "ὄαρ", "AR_ROOT", "Gattin", PHYS, "Greek", is_doubtful=True)
add("GR_OARIZO", "ὀαρίζω", "GR_OAR", "habe vertrauten Umgang", PHYS, "Greek")
add("GR_CHALKOARAS", "χαλκο-άρας", "AR_ROOT", "erzgefügt, gepanzert", PHYS, "Greek")
add("GR_CHERIARAS", "χερι-άρας", "AR_ROOT", "(attested with τέκτων, Pindar)", PHYS, "Greek")
add("GR_ARTHRON", "ἄρ-θρον", "AR_ROOT", "Glied, Gelenk", PHYS, "Greek")
add("GR_ARTHMOS", "ἀρθμός", "AR_ROOT", "Verbindung, Freundschaft", PHYS, "Greek")
add("GR_ARTHMIOS", "ἄρθμιος", "GR_ARTHMOS", "vereint", PHYS, "Greek")
add("HOMER_DAMART", "δάμ-αρ-τ-", "AR_ROOT", "Hausfrau", PHYS, "Homeric-Greek")
add("AEOL_DOMORTIS", "δόμορτις", "HOMER_DAMART", "Hausfrau", PHYS, "Aeolic-Greek")
add("GR_PYLARTES", "πυλάρτης", "AR_ROOT", "Hades als Verschließer des Unterweltstores", PHYS, "Greek")
add("GR_ARESKO", "ἀρέσκω", "AR_ROOT", "gleiche aus, mache gut, befriedige", PHYS, "Greek")
add("GR_ARESKEIMOI", "ἀρέσκει μοι", "GR_ARESKO", "es paßt, gefällt mir", PHYS, "Greek")
add("GR_ARESKESTHAI", "ἀρέσκεσθαι", "GR_ARESKO", "sich verständigen, einig werden mit jemandem; sich geneigt machen, versöhnen", PHYS, "Greek")
add("GR_ARESSASTHAI", "ἀρέσσασθαι", "GR_ARESKO", "sich verständigen, einig werden mit jemandem; sich geneigt machen, versöhnen", PHYS, "Greek")
add("GR_ARETE", "ἀρετή", "AR_ROOT", "Tüchtigkeit", PHYS, "Greek")
add("GR_AREION", "ἀρείων", "AR_ROOT", "besser", PHYS, "Greek")
add("GR_ARI", "ἀρι-", "AR_ROOT", "sehr (Präfix in Kompositis)", PHYS, "Greek", is_doubtful=True)
add("GR_ARISTOS", "ἄριστος", "GR_AREION", "besser, best", PHYS, "Greek")
add("GR_ARISTEROS", "ἀριστερός", "AR_ROOT", "links", PHYS, "Greek")
add("GR_THYMERES", "θυμ-ήρης", "AR_ROOT", "wohlgefällig (mit Dehnung)", PHYS, "Greek")
add("GR_HOMEROS_N", "ὅμηρος", "AR_ROOT", "Gatte; Geisel, Unterpfand (mit Dehnung)", PHYS, "Greek")
add("GR_HOMEREO", "ὁμηρέω", "GR_HOMEROS_N", "treffe zusammen (mit Dehnung)", PHYS, "Greek")
add("GR_HOMEROS_PN", "̓́Ομηρος", "GR_HOMEROS_N", "Begleiter, der Blinde, der mit seinem Führer geht (mit Dehnung)", PHYS, "Greek")
add("POLN_KOJARZYC", "ko-jarzyć", "AR_ROOT", "knüpfen, verbinden, vereinigen", PHYS, "Polish", is_doubtful=True)
add("TOCHA_ARWAR", "ārwar", "AR_ROOT", "bereit", PHYS, "Tocharian-A")
add("TOCHB_ARWER", "ārwer / ārwar", "TOCHA_ARWAR", "bereit", PHYS, "Tocharian-B")
add("TOCHA_AREM", "aräm", "AR_ROOT", "Gesicht", PHYS, "Tocharian-A")
add("TOCHB_ERE", "ere", "TOCHA_AREM", "Gesicht", PHYS, "Tocharian-B")

# --- t-Bildungen: r̥t-, art- 'zusammengefügt' ---
TBIL = "t-Bildungen: r̥t-, art- 'zusammengefügt'"
add("AR_TBIL", TBIL, "AR_ROOT", TBIL, PHYS, "PIE-root")
add("AI_RTA", "r̥tá-", "AR_TBIL", "passend, recht", PHYS, "Sanskrit")
add("AI_RTAM", "r̥tám", "AR_TBIL", "wohlgefügte, heilige Ordnung", PHYS, "Sanskrit")
add("AI_RTENA", "r̥tēna", "AI_RTA", "rite", PHYS, "Sanskrit")
add("AV_ARETA", "arəta- / ərəta-", "AR_TBIL", "Gesetz, Recht, heiliges Recht", PHYS, "Avestan")
add("APERS_ARTA", "arta-", "AV_ARETA", "Gesetz, Recht, heiliges Recht", PHYS, "Old-Persian")
add("AV_ASHA", "aša-", "AR_TBIL", "was recht, wahr ist", PHYS, "Avestan")
add("AI_RTAVANT", "r̥tāvan(t)-", "AI_RTA", "ordnungsgemäß, gerecht", PHYS, "Sanskrit")
add("AV_ASHAVAN", "ašā̆van/t/-", "AI_RTAVANT", "ordnungsgemäß, gerecht", PHYS, "Avestan")
add("AI_RTUH", "r̥tú-ḥ", "AR_TBIL", "bestimmte Zeit, Ordnung, Regel", PHYS, "Sanskrit")
add("AI_RTIH", "r̥tí-ḥ", "AR_TBIL", "Art, Weise", PHYS, "Sanskrit")
add("AV_AIPIARETA", "aipi-ərəta-", "AR_TBIL", "bestimmt, fest zugewiesen", PHYS, "Avestan")
add("ARM_ARD1", "ard", "AR_TBIL", "struttura, costruzione, ornamento", PHYS, "Armenian")
add("ARM_ZARD", "z-ard", "ARM_ARD1", "apparatus, ornatus", PHYS, "Armenian")
add("ARM_ARD2", "ard", "AR_TBIL", "soeben, jetzt", PHYS, "Armenian", paradigm_id="PARA_ARD2_ARTI")
add("ARM_ARDAR", "ardar", "AR_TBIL", "gerecht", PHYS, "Armenian")
add("AV_AREDRA", "arədra-", "ARM_ARDAR", "getreu, zuverlässig, glaubenstreu, fromm", PHYS, "Avestan", is_doubtful=True)
add("ARM_ARDIUN", "ardiun", "AR_TBIL", "struttura", PHYS, "Armenian")
add("GR_HAMARTE", "ἁμαρτή", "AR_TBIL", "gleichzeitig", PHYS, "Greek")
add("GR_HOMARTEO", "ὁμ-αρτέω", "AR_TBIL", "schließe mich an jemanden an, begleite", PHYS, "Greek")
add("GR_ARTIFEPES", "ἀρτι-Fεπής", "AR_TBIL", "des Wortgefüges kundig", PHYS, "Greek")
add("GR_ARTIPOUS", "ἀρτί-πο(υ)ς", "AR_TBIL", "mit gesunden Füßen", PHYS, "Greek")
add("GR_ARTIFRON", "ἀρτί-φρων", "AR_TBIL", "mit fest(gefügt)em Verstande", PHYS, "Greek")
add("GR_ARTAMOS", "ἄρταμος", "AR_TBIL", "Schlächter; Mörder", PHYS, "Greek", is_doubtful=True)
add("GR_ARTAMEO", "ἀρταμέω", "GR_ARTAMOS", "schlachte, zerstückle", PHYS, "Greek")
add("GR_ARTEMES", "ἀρτεμής", "AR_TBIL", "frisch und gesund", PHYS, "Greek", is_doubtful=True)
add("GR_ARTI", "ἄρτι", "AR_TBIL", "eben, gerade", PHYS, "Greek", paradigm_id="PARA_ARD2_ARTI")
add("ARM_ARDACIN", "ard-a-cin", "ARM_ARD2", "neugeboren", PHYS, "Armenian")
add("GR_APARTI", "ἀπ-αρτί", "GR_ARTI", "genau, gerade", PHYS, "Greek")
add("GR_ARTIOS", "ἄρτιος", "GR_ARTI", "angemessen, gerade, vollkommen", PHYS, "Greek")
add("GR_ARTIAZO", "ἀρτιάζω", "GR_ARTIOS", "spiele gerade oder ungerade", PHYS, "Greek")
add("GR_ARTIZO", "ἀρτίζω", "GR_ARTI", "mache fertig, bereite", PHYS, "Greek")
add("GR_ARSION", "ἄρσιον", "AR_TBIL", "δίκαιον", PHYS, "Greek")
add("GR_ANARSIOS", "ἀνάρσιος", "GR_ARSION", "feindlich", PHYS, "Greek")
add("GR_EPARTES", "ἐπαρτής", "AR_TBIL", "gerüstet", PHYS, "Greek")
add("GR_ARTYN", "ἀρτύν", "AR_TBIL", "φιλίαν καὶ σύμβασιν", PHYS, "Greek")
add("GR_ARTYS", "ἀρτύς", "AR_TBIL", "σύνταξις", PHYS, "Greek", paradigm_id="PARA_ARTYS_ARTUS")
add("GR_ARTYO", "ἀρτύω", "GR_ARTYS", "füge zusammen, bereite", PHYS, "Greek")
add("GR_ARTYNO", "ἀρτύνω", "GR_ARTYS", "füge zusammen, bereite", PHYS, "Greek")
add("GR_ARTYNAS", "ἀρτύ̄νας", "AR_TBIL", "Beamtentitel (Argos, Epidauros, Thera)", PHYS, "Greek")
add("GR_ARTYNOS", "ἄρτῡνος", "GR_ARTYNAS", "Beamtentitel (Argos, Epidauros, Thera)", PHYS, "Greek")
add("GR_ARTYTER", "ἀρτῡτήρ", "GR_ARTYNAS", "Beamtentitel (Argos, Epidauros, Thera)", PHYS, "Greek")
add("LAT_ARTUS_ENG", "artus / artē", "AR_TBIL", "eng in Raum und Zeit, straff", PHYS, "Latin")
add("LAT_ARS", "ars", "AR_TBIL", "die Geschicklichkeit, Kunst, Art und Weise", PHYS, "Latin", paradigm_id="PARA_ARS_MHDART")
add("LAT_INERS", "in-ers", "LAT_ARS", "kunstlos, träge", PHYS, "Latin")
add("LAT_SOLLERS", "soll-ers", "LAT_ARS", "geschickt", PHYS, "Latin")
add("LAT_ALLERS", "allers / alers", "LAT_ARS", "gelehrt", PHYS, "Latin")
add("LAT_ARTIO", "artiō / artāre", "AR_TBIL", "fest zusammenfügen, zusammenpressen", PHYS, "Latin")
add("LAT_ARTUS_GEL", "artus", "AR_TBIL", "Gelenk, Glied", PHYS, "Latin", paradigm_id="PARA_ARTYS_ARTUS")
add("LAT_ARTICULUS", "articulus", "LAT_ARTUS_GEL", "Gelenk, Glied; Augenblick, Wendepunkt", PHYS, "Latin")
add("LIT_ARTI", "artì", "AR_TBIL", "nahe", PHYS, "Lithuanian")
add("MHD_ART", "art", "AR_TBIL", "Art und Weise", PHYS, "Middle-High-German", paradigm_id="PARA_ARS_MHDART")
add("ANORD_EINARDR", "ein-arđr", "AR_TBIL", "einfach, aufrichtig", PHYS, "Old-Norse")
add("ANORD_EINORD", "einǫrd", "ANORD_EINARDR", "Zuverlässigkeit", PHYS, "Old-Norse")
add("TOCHB_ARTKYE", "ar(t)kye", "AR_TBIL", "reich, wertvoll", PHYS, "Tocharian-B", is_doubtful=True)

# --- m-Bildungen; leichte Basis ar- ---
MBIL1 = "m-Bildungen; Von der leichten Basis ar-"
add("AR_MBIL1", MBIL1, "AR_ROOT", MBIL1, PHYS, "PIE-root")
add("ARM_YARMAR", "y-armar", "AR_MBIL1", "passend, angemessen", PHYS, "Armenian")
add("GR_HARMOS", "ἁρμός", "AR_MBIL1", "Fuge, Zusammenfügung, Gelenk", PHYS, "Greek")
add("GR_HARMOI", "ἁρμοῖ", "AR_MBIL1", "eben, jüngst", PHYS, "Greek")
add("GR_HARMOZO", "ἁρμόζω", "GR_HARMOI", "verbinde, füge zusammen, passe an, ordne", PHYS, "Greek")
add("GR_HARMONIA", "ἁρμονία", "GR_HARMOI", "Verbindung, Bund, Ebenmaß, Einklang", PHYS, "Greek")
add("GR_HARMA", "ἅρμα", "AR_MBIL1", "Wagen", PHYS, "Greek")
add("GR_HARMALIA", "ἁρμαλιά", "AR_MBIL1", "zugeteilte Nahrung, Proviant", PHYS, "Greek")
add("LAT_ARMA", "arma", "AR_MBIL1", "Gerätschaften, Rüstzeug, Waffen", PHYS, "Latin")
add("LAT_ARMENTUM", "armentum", "AR_MBIL1", "Rudel von Pferden oder Rindern", PHYS, "Latin")
add("ANORD_JORMUNI", "jǫrmuni", "LAT_ARMENTUM", "Rind, Pferd", PHYS, "Old-Norse", is_doubtful=True)
add("GOT_AIRMANAREIKS", "*Aírmana-reiks", "ANORD_JORMUNI", "(Personenname)", PHYS, "Gothic")
add("AGS_EORMENRIC", "Eormenrīc", "GOT_AIRMANAREIKS", "(Personenname)", PHYS, "Anglo-Saxon")
add("AISL_JORMUNREKR", "Jǫrmunrekr", "GOT_AIRMANAREIKS", "(Personenname)", PHYS, "Old-Icelandic")
add("MHD_ERMENRICH", "Ermenrīch", "GOT_AIRMANAREIKS", "(Personenname)", PHYS, "Middle-High-German")
add("LAT_ERMUNDURI", "Ermunduri", "ANORD_JORMUNI", "Großthüringer (Stammesname)", PHYS, "Latin")
add("ANORD_JORMUNGRUND", "jǫrmungrund", "ANORD_JORMUNI", "die weite Erde", PHYS, "Old-Norse", paradigm_id="PARA_JORMUNGRUND")
add("AGS_EORMENGRUND", "eormengrund", "ANORD_JORMUNI", "die weite Erde", PHYS, "Anglo-Saxon", paradigm_id="PARA_JORMUNGRUND")
add("AHD_IRMINDEOT", "irmindeot", "ANORD_JORMUNGRUND", "(no gloss printed)", PHYS, "OHG")
add("AS_IRMINSUL", "Irmin-sūl", "ANORD_JORMUNGRUND", "(Personen-/Ortsname)", PHYS, "Old-Saxon")
add("LAT_HERMINONES", "Herminones", "ANORD_JORMUNI", "(Stammesname, Kurzform)", PHYS, "Latin")
add("AKSL_JARMU", "jarьmъ", "AR_MBIL1", "Joch", PHYS, "Church-Slavonic")
add("SLOVEN_JERMEN", "jérmen", "AKSL_JARMU", "Jochriemen, Riemen", PHYS, "Slovenian")
add("AKSL_REMEN", "remenь", "AR_MBIL1", "Riemen", PHYS, "Church-Slavonic")
add("SERB_REMEN", "rè́mēn", "AKSL_REMEN", "Riemen", PHYS, "Serbian")
add("TOCHB_YARM", "yarm", "AR_MBIL1", "Maß", PHYS, "Tocharian-B")
add("TOCHAB_YAERM", "yärm", "TOCHB_YARM", "Maß", PHYS, "Tocharian-AB")

# --- m-Bildungen; schwere Basis arə-mo-: r̥̄-mo- 'Arm' ---
MBIL2 = "m-Bildungen; Von der schweren Basis arə-mo-: r̥̄-mo- 'Arm'"
add("AR_MBIL2", MBIL2, "AR_ROOT", MBIL2, BODY, "PIE-root")
add("AI_IRMAH", "īrmá-ḥ", "AR_MBIL2", "Arm, Vorderbug", BODY, "Sanskrit")
add("AV_AREMA", "arəma-", "AI_IRMAH", "Arm", BODY, "Avestan")
add("OSSET_AERM", "ärm", "AR_MBIL2", "hohle Hand", BODY, "Ossetic")
add("OSSET_AELMAERIN", "älm-ärịn / ärm-ärịn", "OSSET_AERM", "Ellenbogen", BODY, "Ossetic")
add("LAT_ARMUS", "armus", "AR_MBIL2", "der oberste Teil des Oberarms, Schulterblatt, bei Tieren der Vorderbug", BODY, "Latin")
add("GALL_ARAMO", "aramō", "AR_MBIL2", "Gabelung", BODY, "Gallic")
add("GALL_ARAMONES", "*aramones", "GALL_ARAMO", "Scherenarme der Deichsel", BODY, "Gallic")
add("APR_IRMO", "irmo", "AR_MBIL2", "Arm", BODY, "Old-Prussian")
add("LIT_IRMEDE", "ìrmėdė", "AR_MBIL2", "Gicht in den Gelenken", BODY, "Lithuanian")
add("LIT_IRMLIGA", "irm-liga", "LIT_IRMEDE", "Gicht", BODY, "Lithuanian")
add("LIT_ARMAI", "armaĩ", "AR_MBIL2", "Vorderarm am Wagen", BODY, "Lithuanian-Žemaitian")
add("AKSL_RAMO", "ramo / ramę", "AR_MBIL2", "Schulter", BODY, "Church-Slavonic")
add("SERB_RAME", "rà́me", "AKSL_RAMO", "Schulter", BODY, "Serbian")
add("GOT_ARMS", "arms", "AR_MBIL2", "Arm", BODY, "Gothic")
add("AHD_ARM", "arm", "GOT_ARMS", "Arm", BODY, "OHG")
add("ARM_ARMUKN", "armukn", "AR_MBIL2", "Ellenbogen", BODY, "Armenian")

# --- Wzf. rē-, rə- ---
WZFRE = "Wzf. rē-, rə-"
add("AR_WZFRE", WZFRE, "AR_ROOT", WZFRE, PHYS, "PIE-root")
add("LAT_REOR", "reor / rērī", "AR_WZFRE", "berechnen, meinen, dafürhalten", PHYS, "Latin")
add("LAT_RATUS", "ratus", "LAT_REOR", "in der Meinung, berechnet, bestimmt, gültig, rechtskräftig", PHYS, "Latin")
add("LAT_RATIO", "ratiō", "LAT_REOR", "Berechnung, Erwägung, Vernunft, Beweggrund, Grund", PHYS, "Latin")
add("LAT_PROPORTIO", "(prō)portiō", "LAT_RATIO", "(no gloss printed)", PHYS, "Latin", is_doubtful=True)
add("GOT_GARATHJAN", "*garaþjan / garaþana", "AR_WZFRE", "zählen", PHYS, "Gothic")
add("ANORD_HUNDRADH", "hundrađ", "AR_WZFRE", "hundert", PHYS, "Old-Norse")
add("NHD_HUNDERT", "Hundert", "ANORD_HUNDRADH", "Hundert", PHYS, "German")
add("LAT_RATUM", "rătum", "ANORD_HUNDRADH", "Zahl", PHYS, "Latin")
add("AHD_GIRAD", "girad", "AR_WZFRE", "gerad (nur von Zahlen)", PHYS, "OHG")
add("NHD_GERAD", "gerad", "AHD_GIRAD", "gerad (nur von Zahlen)", PHYS, "German")
add("ANORD_TIROEDR", "tī-rø̄đr", "AR_WZFRE", "nach Zehnern gezählt", PHYS, "Old-Norse")
add("GOT_RATHJO", "raþjō", "AR_WZFRE", "Zahl, Rechnung, Rechenschaft", PHYS, "Gothic")
add("AS_RETHIA", "rethia", "AR_WZFRE", "Rechenschaft", PHYS, "Old-Saxon")
add("AHD_RADJA", "radja / redea", "AR_WZFRE", "Rechenschaft, Rede und Antwort, Rede, Erzählung", PHYS, "OHG")
add("AFRIES_BIRETHIA", "birethia", "AR_WZFRE", "anklagen", PHYS, "Old-Frisian")
add("AS_RETHION", "rethiōn", "AR_WZFRE", "reden", PHYS, "Old-Saxon")
add("AHD_REDION", "red(i)ōn", "AS_RETHION", "reden", PHYS, "OHG")
add("ANORD_ROEDH", "rǫđ", "AR_WZFRE", "Reihe, bes. dem Strande entlang ziehende Erhöhung", PHYS, "Old-Norse", is_doubtful=True)
add("MND_RAT_REIHE", "rat", "ANORD_ROEDH", "Reihe", PHYS, "Middle-Low-German", is_doubtful=True)
add("AHD_RAMEN", "rāmen", "AR_WZFRE", "nach etwas trachten, streben, zielen", PHYS, "OHG")
add("AS_ROMON", "rōmon", "AHD_RAMEN", "streben", PHYS, "Old-Saxon")
add("MHD_RAM", "rām", "AHD_RAMEN", "Ziel", PHYS, "Middle-High-German")
add("MND_RAM", "rām", "AHD_RAMEN", "Ziel", PHYS, "Middle-Low-German")

# --- dh-Erweiterung rē-dh-, rō-dh-, rə-dh- ---
REDH = "dh-Erweiterung rē-dh-, rō-dh-, rə-dh-"
add("AR_REDH", REDH, "AR_WZFRE", REDH, PHYS, "PIE-root")
add("AI_RADHNOTI", "rādhnṓti", "AR_REDH", "macht (passend) zurecht, bringt zustande; gerät, gelingt, hat Glück womit; befriedigt, gewinnt jemanden", PHYS, "Sanskrit")
add("AI_RADHYATI", "rā́dhyati", "AI_RADHNOTI", "macht (passend) zurecht, bringt zustande; gerät, gelingt, hat Glück womit; befriedigt, gewinnt jemanden", PHYS, "Sanskrit")
add("AI_RADHAYATI", "rādhayati", "AI_RADHNOTI", "bringt zustande, befriedigt", PHYS, "Sanskrit")
add("AI_RADHAH", "rādha-ḥ / rādhaḥ", "AI_RADHNOTI", "Segen, Gelingen, Wohltat, Gabe, Freigebigkeit", PHYS, "Sanskrit")
add("AV_RADHAITI", "rāδaiti", "AR_REDH", "macht bereit", PHYS, "Avestan")
add("AV_RADHA", "rāδa-", "AR_REDH", "Fürsorger", PHYS, "Avestan")
add("AV_RADAH", "rādah-", "AR_REDH", "Sichbereitstellen, Bereitwilligkeit (in religiöser Hinsicht)", PHYS, "Avestan")
add("APERS_RADIY", "rādiy", "AR_REDH", "wegen", PHYS, "Old-Persian")
add("NPERS_ARAYAD", "ārāyad / ārāstan", "AR_REDH", "schmücken", PHYS, "New-Persian")
add("AIR_IMMRADIM", "imm-rādim", "AR_REDH", "überlege, überdenke", PHYS, "Old-Irish")
add("ACYMR_AMRAUD", "amraud", "AR_REDH", "mens", PHYS, "Old-Welsh")
add("NCYMR_AMRAWDD", "amrawdd", "ACYMR_AMRAUD", "Gespräch", PHYS, "New-Welsh")
add("AIR_NORAIDIU", "no-rāidiu / no-rādim", "AR_REDH", "sage", PHYS, "Old-Irish")
add("MCYMR_ADRAWD", "adrawd", "AIR_NORAIDIU", "erzählen", PHYS, "Middle-Welsh")
add("GOT_RODJAN", "rōdjan", "AIR_NORAIDIU", "reden", PHYS, "Gothic")
add("ANORD_ROEDHA", "rø̄đa", "GOT_RODJAN", "reden", PHYS, "Old-Norse")
add("NHD_REDE", "Rede", "GOT_RODJAN", "Rede", PHYS, "German", is_doubtful=True)
add("NHD_REDEN", "reden", "GOT_RODJAN", "reden", PHYS, "German", is_doubtful=True)
add("GOT_GAREDAN", "garēdan", "AR_REDH", "worauf bedacht sein, Vorsorge treffen", PHYS, "Gothic")
add("GOT_URREDAN", "urrēdan", "AR_REDH", "urteilen, bestimmen", PHYS, "Gothic")
add("GOT_UNDREDAN", "undrēdan", "AR_REDH", "besorgen, gewähren", PHYS, "Gothic")
add("AHD_RATAN", "rātan", "AR_REDH", "raten, beratschlagen, worauf sinnen, anstiften, deuten (Rätsel), auffordern, wofür sorgen, verschaffen", PHYS, "OHG")
add("AS_RADAN", "rādan", "AHD_RATAN", "raten, beratschlagen, worauf sinnen, anstiften, deuten (Rätsel), auffordern, wofür sorgen, verschaffen", PHYS, "Old-Saxon")
add("ANORD_RADHA", "rāđa", "AHD_RATAN", "raten, beratschlagen, worauf sinnen, anstiften, deuten (Rätsel), auffordern, wofür sorgen, verschaffen", PHYS, "Old-Norse")
add("AGS_RAEDAN", "rǣdan", "AHD_RATAN", "raten, beratschlagen, worauf sinnen, anstiften, deuten (Rätsel), auffordern, wofür sorgen, verschaffen; lesen", PHYS, "Anglo-Saxon")
add("ENG_READ", "read", "AGS_RAEDAN", "lesen", PHYS, "English")
add("AHD_RAT", "rāt", "AR_REDH", "vorhandene Mittel, Rat, Ratschlag, Überlegung, Entschluß, Absicht, Vorsorge, Vorrat", PHYS, "OHG")
add("AS_RAD", "rād", "AHD_RAT", "vorhandene Mittel, Rat, Ratschlag, Überlegung, Entschluß, Absicht, Vorsorge, Vorrat", PHYS, "Old-Saxon")
add("ANORD_RAD", "rād", "AHD_RAT", "vorhandene Mittel, Rat, Ratschlag, Überlegung, Entschluß, Absicht, Vorsorge, Vorrat", PHYS, "Old-Norse")
add("AGS_RAED", "rǣd", "AHD_RAT", "vorhandene Mittel, Rat, Ratschlag, Überlegung, Entschluß, Absicht, Vorsorge, Vorrat", PHYS, "Anglo-Saxon")
add("AKSL_RADITI", "raditi", "AIR_NORAIDIU", "sorgen", PHYS, "Church-Slavonic")
add("SERB_RADIM", "râdîm / ráditi", "AKSL_RADITI", "arbeiten, trachten", PHYS, "Serbian")
add("SERB_RAD", "rad", "AKSL_RADITI", "Geschäft, Arbeit", PHYS, "Serbian")
add("AKSL_RADI", "radi", "APERS_RADIY", "wegen", PHYS, "Church-Slavonic")
add("AKSL_NERODU", "nerodъ", "AKSL_RADITI", "Vernachlässigung", PHYS, "Church-Slavonic")
add("SLOVEN_RODIM", "rǫ́dim / rǫ́diti", "AKSL_NERODU", "sorgen, sich kümmern", PHYS, "Slovenian")

# --- Wzf. (a)rī̆-, rēi- ---
WZFREI = "Wzf. (a)rī̆-, rēi-"
add("AR_WZFREI", WZFREI, "AR_ROOT", WZFREI, PHYS, "PIE-root")
add("GR_ARITHMOS", "ἀριθμός", "AR_WZFREI", "Zahl", PHYS, "Greek")
add("GR_NERITOS", "νήριτος", "AR_WZFREI", "ungezählt", PHYS, "Greek")
add("ARKAD_EPARITOS", "ἐπάριτος", "AR_WZFREI", "ἐπίλεκτος, auserlesen", PHYS, "Arcadian-Greek")
add("GR_ARIMAZEI", "ἀριμάζει", "AR_WZFREI", "ἁρμόζει", PHYS, "Greek")
add("LAT_RITUS", "rītus", "AR_WZFREI", "hergebrachte Art der Religionsübung, Gebrauch, Sitte, Gewohnheit, Art", PHYS, "Latin")
add("LAT_RITE", "rīte", "LAT_RITUS", "in passender Art, nach dem rechten religiösen Gebrauch", PHYS, "Latin")
add("AIR_RIM", "rīm", "AR_WZFREI", "Zahl", PHYS, "Old-Irish")
add("AIR_ARAM", "āram", "AIR_RIM", "Zahl", PHYS, "Old-Irish")
add("AIR_DORIMU", "do-rīmu", "AIR_RIM", "zähle", PHYS, "Old-Irish")
add("CYMR_RHIF", "rhif", "AIR_RIM", "Zahl", PHYS, "Welsh")
add("ANORD_RIM", "rīm", "AIR_RIM", "Rechnung, Berechnung", PHYS, "Old-Norse")
add("AS_UNRIM", "unrīm", "AIR_RIM", "Unzahl", PHYS, "Old-Saxon")
add("AGS_RIM", "rīm", "AIR_RIM", "Zahl", PHYS, "Anglo-Saxon")
add("AHD_RIM", "rīm", "AIR_RIM", "Reihe, Reihenfolge, Zahl", PHYS, "OHG")
add("MHD_RIM", "rīm", "AHD_RIM", "Vers, Reim", PHYS, "Middle-High-German")
add("LAT_RES", "rēs", "AR_WZFREI", "Sache", PHYS, "Latin", is_doubtful=True)
add("AKSL_ORANDIJE", "orądije", "AR_WZFREI", "apparatus, instrumentum", PHYS, "Church-Slavonic", is_doubtful=True)
add("AKSL_REDU", "rędъ", "AR_WZFREI", "Ordnung", PHYS, "Church-Slavonic", is_doubtful=True)
add("LIT_RINDA", "rínda", "AR_WZFREI", "Reihe", PHYS, "Lithuanian", is_doubtful=True)
add("LETT_RINDA", "riñda", "AR_WZFREI", "Reihe, Zahl", PHYS, "Latvian", is_doubtful=True)
add("GR_ORDEO", "ὀρδέω", "AR_WZFREI", "lege ein Gewebe an", PHYS, "Greek", is_doubtful=True)
add("GR_ORDIKON", "ὀρδικόν", "GR_ORDEO", "τὸν χιτωνίσκον", PHYS, "Greek", is_doubtful=True)
add("GR_ORDEMA", "ὄρδημα", "GR_ORDEO", "ἡ τολύπη τῶν ἐρίων", PHYS, "Greek", is_doubtful=True)
add("LAT_ORDIOR", "ōrdior / ōrsus sum", "GR_ORDEO", "anzetteln, anreihen, anfangen, beginnen", PHYS, "Latin", is_doubtful=True)
add("LAT_EXORDIOR", "exōrdior", "LAT_ORDIOR", "zettle ein Gewebe an", PHYS, "Latin", is_doubtful=True)
add("LAT_REDORDIOR", "redōrdior", "LAT_ORDIOR", "hasple ab", PHYS, "Latin", is_doubtful=True)
add("LAT_ORDO", "ōrdo", "LAT_ORDIOR", "Reihe, Ordnung", PHYS, "Latin", is_doubtful=True)
add("UMBR_URNASIER", "urnasier", "LAT_ORDO", "(= lat. ordinariis?)", PHYS, "Umbrian", is_doubtful=True)
add("GR_ARACHNE", "ἀράχνη", "AR_WZFREI", "Spinne", PHYS, "Greek", is_doubtful=True)
add("LAT_ARANEUS", "arāneus", "GR_ARACHNE", "zur Spinne gehörig", PHYS, "Latin", is_doubtful=True)
add("LAT_ARANEA", "arānea", "GR_ARACHNE", "Spinne", PHYS, "Latin", is_doubtful=True)
add("GR_ARKYS", "ἄρκυς", "AR_WZFREI", "Netz", PHYS, "Greek", is_doubtful=True)
add("GR_ARKANE", "ἀρκάνη", "GR_ARKYS", "τὸ ῥάμμα ᾡ τὸν στήμονα ἐγκαταπλέκουσιναἱ διαζόμεναι", PHYS, "Greek", is_doubtful=True)
add("LETT_ERKULS", "er'kuls", "GR_ARKYS", "Spindel; Wickel von Heede zum Spinnen", PHYS, "Latvian", is_doubtful=True)

# --- dh-Erweiterung rēi-dh- ---
REIDH = "dh-Erweiterung rēi-dh-"
add("AR_REIDH", REIDH, "AR_WZFREI", REIDH, PHYS, "PIE-root", is_doubtful=True)
add("GOT_GARAITHS", "garaiþs", "AR_REIDH", "angeordnet, bestimmt", PHYS, "Gothic", is_doubtful=True)
add("GOT_RAIDJAN", "raidjan", "AR_REIDH", "verordnen, bestimmen", PHYS, "Gothic", is_doubtful=True)
add("GOT_GARAIDJAN", "garaidjan", "GOT_RAIDJAN", "verordnen, bestimmen", PHYS, "Gothic", is_doubtful=True)
add("ANORD_GREIDHR", "g-reiđr", "AR_REIDH", "bereit, leicht, klar", PHYS, "Old-Norse", is_doubtful=True)
add("ANORD_GREIDHA", "greiđa", "ANORD_GREIDHR", "auseinanderwickeln, ordnen, zurechtlegen, zustande bringen, entrichten, zahlen", PHYS, "Old-Norse", is_doubtful=True)
add("MHD_REITEN", "reiten", "AR_REIDH", "zurüsten, bereiten, zählen, rechnen, berechnen, bezahlen", PHYS, "Middle-High-German", is_doubtful=True)
add("MHD_REITE", "reite", "MHD_REITEN", "bereit", PHYS, "Middle-High-German", is_doubtful=True)
add("MHD_GEREITE", "gereite", "MHD_REITEN", "bereit", PHYS, "Middle-High-German", is_doubtful=True)
add("MHD_BEREITE", "bereite", "MHD_REITEN", "bereit", PHYS, "Middle-High-German", is_doubtful=True)
add("AHD_BIREITI", "bireiti", "MHD_BEREITE", "bereit", PHYS, "OHG", is_doubtful=True)
add("AHD_ANTREITI", "antreitī", "AR_REIDH", "series, ordo", PHYS, "OHG", is_doubtful=True)
add("LETT_RIEDU", "riedu / rizt", "AR_REIDH", "ordnen", PHYS, "Latvian", is_doubtful=True)
add("LETT_RAIDS", "raids", "AR_REIDH", "bereit, fertig", PHYS, "Latvian", is_doubtful=True)
add("LETT_RIDI", "ridi / ridas", "AR_REIDH", "Gerät, Kram", PHYS, "Latvian", is_doubtful=True)

# --- Validate referential integrity ---
ids = {r["id"] for r in rows}
for r in rows:
    if r["parent_id"] and r["parent_id"] not in ids:
        raise ValueError(f"row {r['id']} has unresolved parent_id {r['parent_id']!r}")

paradigm_counts = {}
for r in rows:
    if r["paradigm_id"]:
        paradigm_counts[r["paradigm_id"]] = paradigm_counts.get(r["paradigm_id"], 0) + 1
for pid, count in paradigm_counts.items():
    if count < 2:
        raise ValueError(f"paradigm_id {pid} only used by {count} row(s) - not a real pair")

with open("multilingual_tree_data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=["id", "word", "parent_id", "meaning", "category", "tags",
                       "paradigm_id", "is_doubtful"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote multilingual_tree_data.csv: {len(rows)} rows, "
      f"{sum(1 for r in rows if r['is_doubtful'])} flagged doubtful, "
      f"{len(paradigm_counts)} cognate pairs linked via paradigm_id.")
