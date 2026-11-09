# =============================================================================
# lag_kodeark_uttrekk4.R  (extract 4)
#
# Splits an Atekst/Retriever export (RTF, Word or plain text) into individual
# articles and creates:
#   - a CSV file with one row per article (locked copy of the text, also used
#     as input to the LLM extraction)
#   - an Excel sheet for manual coding of:
#       1) relevance  (is the story about the opening of a bike path?)
#       2) location   (where is the bike path?)
#       3) date       (when does / did the bike path open?)
#
# The date in the Atekst page header ("... (Atekst) Dato 04.11.2026") is
# matched with a general pattern, so a new export date does not matter.
#
# Column names are kept in Norwegian so the output can be stacked with the
# files from extracts 1-3.
#
# Packages: rmarkdown + pandoc (for .rtf; pandoc ships with RStudio),
#           officer (only for .docx), openxlsx
# =============================================================================

library(openxlsx)

# ---- Settings ---------------------------------------------------------------
# Input file for extract 4. Fill in the file name, e.g.
#   infil <- "new3_bike_road_data_raw.rtf"
# If left as NULL, a file dialog opens and you can pick the file.
infil <- NULL

utfil       <- "koding_sykkelvei_nytt3.xlsx"  # coding sheet (new name, so earlier sheets are not overwritten)
artikkelfil <- "artikler_nytt3.csv"           # locked copy of the text (do not edit)
id_prefiks  <- "D"                            # IDs D0001, D0002 ... (earlier extracts: A, B, C)

# Earlier extracts. Articles already present in one of these are flagged in
# the column 'finnes_fra_for' and left out of the coding sheet.
# Set to NULL to switch the check off.
tidligere_fil <- c("artikler.csv", "artikler_nytt.csv", "artikler_nytt2.csv")

koder <- "KV"      # coder initials, written to the coding sheet
set.seed(2026)     # makes the random coding order reproducible

if (is.null(infil)) infil <- file.choose()
message("Reading: ", infil)

# ---- 1. Read the lines ------------------------------------------------------
# RTF is converted with pandoc. Pandoc turns both paragraphs and manual line
# breaks into separate lines, so words at line ends are not glued together.
les_linjer <- function(fil) {
  if (grepl("\\.rtf$", fil, ignore.case = TRUE)) {
    tmp <- tempfile(fileext = ".txt")
    rmarkdown::pandoc_convert(normalizePath(fil), to = "plain",
                              output = tmp, options = "--wrap=none")
    readLines(tmp, encoding = "UTF-8", warn = FALSE)
  } else if (grepl("\\.docx$", fil, ignore.case = TRUE)) {
    doc <- officer::read_docx(fil)
    s   <- officer::docx_summary(doc)
    s   <- s[s$content_type == "paragraph", ]
    unlist(strsplit(s$text, "\n"))
  } else {
    readLines(fil, encoding = "UTF-8", warn = FALSE)
  }
}

linjer <- les_linjer(infil)
linjer <- enc2utf8(linjer)
linjer <- gsub(" ", " ", linjer, fixed = TRUE)   # non-breaking space -> space
# Control characters (e.g. page breaks from RTF) are invalid in Excel files and
# trigger the message "Excel found a problem with the content"
linjer <- gsub("\\t", " ", linjer)
linjer <- gsub("[\\x01-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]", "", linjer, perl = TRUE)
linjer <- trimws(linjer)

# Drop empty lines so line positions are easy to follow
linjer <- linjer[linjer != ""]

# ---- 2. Find where each article starts -------------------------------------
# Each article starts like this:
#   Nyheter - Norges Handelshøyskole (NHH)(Atekst) Dato 04.11.2026   <- page header
#   Åpnet ny vei etter 35 års ventetid                               <- headline
#   Agderposten | 07.10.2026 | Side: 2-3                             <- source line
#   Jørund Flaa Silje Bratland Roksvåg                               <- byline
#   Første spadetak ...                                              <- body text
# The page header is repeated at every page break, also in the middle of an
# article. It only counts as an article start when a headline and a source
# line follow directly after it.
topp_mønster  <- "Nyheter - .*\\(Atekst\\) Dato \\d{2}\\.\\d{2}\\.\\d{4}"
kilde_mønster <- "\\|\\s*\\d{2}\\.\\d{2}\\.\\d{4}"

er_topp  <- grepl(topp_mønster, linjer)
er_kilde <- grepl(kilde_mønster, linjer)
n_linjer <- length(linjer)
start_pos <- which(er_topp &
                   c(er_kilde[-(1:2)], FALSE, FALSE) &   # source line two lines below
                   !c(er_kilde[-1], FALSE))             # line below (headline) is not a source line
stopifnot("No articles found. Check that the Atekst page header looks as expected." =
            length(start_pos) > 0)

# Lines that are not article text (page numbers, headers, Retriever notices)
støy <- c(
  "^Side \\d+ av \\d+",
  topp_mønster,
  "^Optional\\[©.*\\]$",
  "^Alle artikler er beskyttet av lov om opphavsrett",
  "^må ikke videreformidles utenfor egen organisasjon",
  "^(fra )?Retriever eller den enkelte utgiver",
  "^Les artikkelen ved å klikke her"
)
fjern_støy <- function(x) {
  x <- gsub("Side \\d+ av \\d+", "", x)          # page numbers, also mid-line
  x <- trimws(gsub(topp_mønster, "", x))         # page headers, also mid-line
  x <- x[!Reduce(`|`, lapply(støy[-(1:2)], grepl, x = x))]
  x[x != ""]
}

# The byline is a short line (names, sometimes an e-mail address) without
# digits and without sentence-final punctuation
ser_ut_som_byline <- function(x) {
  ord <- length(strsplit(x, "\\s+")[[1]])
  ord >= 1 && ord <= 10 && !grepl("[.:?!]$", x) && !grepl("\\d", x)
}

# ---- 3. Build one row per article -------------------------------------------
artikler <- lapply(seq_along(start_pos), function(i) {
  t      <- start_pos[i]
  tittel <- linjer[t + 1]
  kilde  <- linjer[t + 2]
  slutt  <- if (i < length(start_pos)) start_pos[i + 1] - 1 else n_linjer
  rest   <- if (slutt >= t + 3) linjer[(t + 3):slutt] else character(0)

  # Source line, e.g. "□ Agderposten Login | 07.10.2026 | Side: 2-3"
  deler <- trimws(strsplit(kilde, "|", fixed = TRUE)[[1]])
  avis  <- trimws(sub("^[^A-Za-z0-9ÆØÅæøåÄÖÜäöüÉé]*\\s", "", deler[1]))  # drop leading icon
  avis  <- trimws(sub("\\s*-?\\s*Login$", "", avis))  # "Agderposten Login" -> "Agderposten"
  dato  <- regmatches(kilde, regexpr("\\d{2}\\.\\d{2}\\.\\d{4}", kilde))
  side  <- sub("^Side:\\s*", "", grep("^Side:", deler, value = TRUE))

  forfatter <- NA_character_
  if (length(rest) > 0 && ser_ut_som_byline(rest[1])) {
    forfatter <- rest[1]
    rest      <- rest[-1]
  }
  # Everything from the copyright line ("Optional[© ...]") onwards is
  # Retriever boilerplate, not article text
  cr <- grep("^Optional\\[", rest)
  if (length(cr)) rest <- rest[seq_len(cr[1] - 1)]
  rest <- fjern_støy(rest)

  data.frame(
    avis      = avis,                                         # newspaper
    publisert = format(as.Date(dato, format = "%d.%m.%Y")),   # publication date, YYYY-MM-DD
    side      = if (length(side)) side[1] else NA_character_, # page (print editions only)
    tittel    = tittel,                                       # headline
    forfatter = forfatter,                                    # byline
    tekst     = paste(rest, collapse = " "),                  # body text
    stringsAsFactors = FALSE
  )
})
artikler <- do.call(rbind, artikler)

artikler$artikkel_id <- sprintf("%s%04d", id_prefiks, seq_len(nrow(artikler)))
artikler$antall_ord  <- ifelse(artikler$tekst == "", 0L,
                               lengths(strsplit(artikler$tekst, "\\s+")))
# Atekst sometimes delivers only headline and byline, without body text
artikler$mangler_tekst <- artikler$antall_ord < 30
# Excel allows at most 32,767 characters per cell
artikler$tekst_avkortet <- nchar(artikler$tekst) > 32000
artikler$tekst <- substr(artikler$tekst, 1, 32000)
artikler <- artikler[, c("artikkel_id", "avis", "publisert", "side", "tittel",
                         "forfatter", "antall_ord", "mangler_tekst",
                         "tekst_avkortet", "tekst")]

# ---- 4. Duplicates within this extract --------------------------------------
# Same newspaper, publication date and headline = same article. Case, spaces
# and punctuation in the headline are ignored. The body text is not used,
# because page breaks can make the text of the same article differ slightly.
# The first occurrence is kept; later ones point to it in 'duplikat_av'.
lag_nokkel <- function(d) tolower(paste(d$avis, d$publisert,
                                        gsub("[^[:alnum:]]", "", d$tittel)))
nokkel <- lag_nokkel(artikler)
artikler$duplikat_av <- artikler$artikkel_id[match(nokkel, nokkel)]
artikler$duplikat_av[artikler$duplikat_av == artikler$artikkel_id] <- NA
artikler$mulig_duplikat <- !is.na(artikler$duplikat_av)

# ---- 5. Overlap with earlier extracts --------------------------------------
# Same matching rule as above. 'finnes_fra_for' holds the ID from the first
# earlier extract in which the article was found (e.g. A0012, B0034, C0101).
artikler$finnes_fra_for <- NA_character_
for (f in tidligere_fil) {
  if (!file.exists(f)) {
    message("Could not find ", f, ". Skipping the check against this extract.")
    next
  }
  gml <- read.csv(f, encoding = "UTF-8", stringsAsFactors = FALSE)
  gml <- gml[!gml$mulig_duplikat, ]
  treff <- gml$artikkel_id[match(lag_nokkel(artikler), lag_nokkel(gml))]
  ny    <- is.na(artikler$finnes_fra_for) & !is.na(treff)
  artikler$finnes_fra_for[ny] <- treff[ny]   # first match wins
  message(sum(!is.na(treff)), " articles already in ", f, ".")
}

# ---- 6. Summary in the console ---------------------------------------------
n_unike <- sum(!artikler$mulig_duplikat)
n_nye   <- sum(!artikler$mulig_duplikat & is.na(artikler$finnes_fra_for))
message("Articles in extract:          ", nrow(artikler))
message("Duplicates within extract:    ", sum(artikler$mulig_duplikat))
message("Unique articles:              ", n_unike)
message("Unique, already in earlier:   ", n_unike - n_nye)
message("Unique and new (to be coded): ", n_nye)
message("Without (or very short) text: ", sum(artikler$mangler_tekst))
message("Check the number of articles against the Atekst search before coding.")

# Locked copy of the text. The same file is used as input to the LLM extraction.
write.csv(artikler, artikkelfil, row.names = FALSE, fileEncoding = "UTF-8")

# ---- 7. Coding sheet -------------------------------------------------------
koding <- artikler[!artikler$mulig_duplikat &        # each article once
                   is.na(artikler$finnes_fra_for), ]  # not coded before
koding <- koding[sample(nrow(koding)), ]            # random order (blind coding)
koding <- data.frame(
  artikkel_id    = koding$artikkel_id,
  avis           = koding$avis,
  publisert      = koding$publisert,
  tittel         = koding$tittel,
  tekst          = ifelse(koding$mangler_tekst,
                          paste("[INGEN ELLER SVÆRT KORT BRØDTEKST I ATEKST]",
                                koding$tekst),
                          koding$tekst),
  relevant       = NA_character_,  # relevance: ja / nei / uklart (yes / no / unclear)
  sted           = NA_character_,  # location, e.g. "Tromsøbrua, Tromsø"
  kommune        = NA_character_,  # municipality
  dato_i_tekst   = NA_character_,  # opening date verbatim, e.g. "Mandag 2. november"
  aapningsdato   = NA_character_,  # opening date as YYYY-MM-DD, YYYY-MM or YYYY
  dato_presisjon = NA_character_,  # date precision: dag / måned / år / ikke oppgitt
  evidens        = NA_character_,  # short quote supporting the coding
  kommentar      = NA_character_,  # comments, borderline cases
  koder          = koder,          # coder
  stringsAsFactors = FALSE
)

# Codebook (kept in Norwegian, identical to extracts 1-3)
kodebok <- data.frame(
  variabel = c("relevant", "sted", "kommune", "dato_i_tekst",
               "aapningsdato", "dato_presisjon", "evidens", "kommentar"),
  definisjon = c(
    "Handler saken om åpning av en sykkelvei (planlagt eller gjennomført)?",
    "Navnet på sykkelveien, strekningen eller stedet, så presist som teksten gir.",
    "Kommunen sykkelveien ligger i.",
    "Åpningsdatoen slik den står i teksten, ordrett.",
    "Åpningsdatoen omregnet til kalenderdato. Bruk publiseringsdatoen til å tolke «mandag» o.l.",
    "Hvor presis datoen i teksten er.",
    "Kort utdrag fra teksten som begrunner kodingen.",
    "Grensetilfeller og usikkerhet."
  ),
  verdier = c(
    "\"ja\", \"nei\", \"uklart\"",
    "Fritekst. Tomt hvis relevant = nei.",
    "Fritekst. Tomt hvis relevant = nei.",
    "Fritekst. Tomt hvis ikke oppgitt.",
    "ÅÅÅÅ-MM-DD, ÅÅÅÅ-MM eller ÅÅÅÅ. Tomt hvis ikke oppgitt.",
    "\"dag\", \"måned\", \"år\", \"ikke oppgitt\"",
    "Fritekst, maks én setning.",
    "Fritekst."
  ),
  beslutningsregel = c(
    "Skriv inn regler for grensetilfeller etter piloten (f.eks. bru som gjenåpner med nytt sykkelfelt).",
    "", "", "",
    "Hvis flere datoer nevnes: bruk datoen for åpning av sykkelveien, ikke anleggsstart e.l.",
    "", "", ""
  ),
  stringsAsFactors = FALSE
)

# Allowed values for the drop-down lists
lister <- list(
  relevant       = c("ja", "nei", "uklart"),
  dato_presisjon = c("dag", "måned", "år", "ikke oppgitt")
)

# ---- 8. Write the Excel file -------------------------------------------------
wb <- createWorkbook()
addWorksheet(wb, "koding")                    # coding sheet
addWorksheet(wb, "kodebok")                   # codebook
addWorksheet(wb, "lister", visible = FALSE)   # hidden sheet with drop-down values

writeData(wb, "lister", data.frame(relevant = lister$relevant), startCol = 1)
writeData(wb, "lister", data.frame(dato_presisjon = lister$dato_presisjon), startCol = 2)

hode <- createStyle(textDecoration = "bold", fgFill = "#DDE6F0",
                    wrapText = TRUE, valign = "top", border = "bottom")  # header row
brod <- createStyle(wrapText = TRUE, valign = "top")                     # article columns
kode <- createStyle(fgFill = "#FFF7D6", wrapText = TRUE, valign = "top") # columns to fill in

writeData(wb, "koding", koding, headerStyle = hode)
n   <- nrow(koding)
rad <- 2:(n + 1)
addStyle(wb, "koding", brod, rows = rad, cols = 1:5, gridExpand = TRUE)
addStyle(wb, "koding", kode, rows = rad, cols = 6:13, gridExpand = TRUE)

# Drop-down lists for the categorical variables
kol <- function(navn) match(navn, names(koding))
dataValidation(wb, "koding", cols = kol("relevant"), rows = rad,
               type = "list", value = "'lister'!$A$2:$A$4")
dataValidation(wb, "koding", cols = kol("dato_presisjon"), rows = rad,
               type = "list", value = "'lister'!$B$2:$B$5")

setColWidths(wb, "koding", cols = seq_along(koding),
             widths = c(10, 14, 11, 30, 90, 10, 22, 14, 18, 14, 13, 35, 30, 7))
freezePane(wb, "koding", firstRow = TRUE, firstCol = TRUE)

writeData(wb, "kodebok", kodebok, headerStyle = hode)
addStyle(wb, "kodebok", brod, rows = 2:(nrow(kodebok) + 1), cols = 1:4,
         gridExpand = TRUE)
setColWidths(wb, "kodebok", cols = 1:4, widths = c(16, 60, 35, 60))

# Note: openxlsx may print a harmless warning about sprintf/dataValidation
saveWorkbook(wb, utfil, overwrite = TRUE)
message("Wrote ", utfil, " and ", artikkelfil)
