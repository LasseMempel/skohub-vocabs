import requests
import pandas as pd
import urllib.parse
from rdflib import Graph, URIRef, BNode, Literal, Namespace
from rdflib.namespace import SKOS, RDF, DC, DCTERMS, RDFS, VANN, XSD

def csv2Df(link, propertyMatchDict):
    with open("data.csv", "w", encoding="utf-8") as f:
        text = requests.get(link).text.encode("ISO-8859-1").decode()
        #text = text.replace("\n"," ")
        f.write(text) 
    df = pd.read_csv('data.csv', encoding="utf-8")
    df.rename(columns=propertyMatchDict, inplace=True) # rename columns according to propertyMatchDict
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x) # remove leading and trailing whitespaces from all cells
    # fix to replace linebreaks with pipeseperators for mapping properties, which don't follow the seperator rules
    for col in ["closeMatch", "relatedMatch", "exactMatch"]:
        if col in df.columns:
            df[col] = df[col].map(lambda x: "|".join(x.split("\n")) if isinstance(x, str) else x)
    return df

def sortNotation(df):
    # generate an array of uuids from the notation column
    uuids = df['notation'].tolist()
    # delete all empty elements
    uuids = [x.strip() for x in uuids if x != "" and not isinstance(x, float)]
    # sort the uuids alphanumerically
    uuids.sort() 
    # iterate over every row and build a notation change dictionary
    i = 0
    changeDict = {}
    for index, row in df.iterrows():
        if row["prefLabel"] and isinstance(row["prefLabel"], str) and row["notation"] and isinstance(row["notation"], str):
            oldNotation = row['notation'].strip()
            newNotation = uuids[i]
            i += 1
            changeDict[oldNotation] = newNotation
    # replace all notations in the df with the new notation
    df.replace(changeDict, inplace=True)
    print("exporting sorted csv...")
    df.to_csv('sortedData.csv', index=False, encoding="utf-8")
    return df

def row2Triple(i, g, concept, pred, obj, isLang, baseLanguageLabel, thesaurusAddendum, thesaurus):
    i = i.strip()
    if i == "":
        print("Empty cell")
        print(concept, pred, obj)
        return g
    if obj == URIRef:
        if pred in [SKOS.broader, SKOS.narrower, SKOS.related]:
            if i != "top":
                g.add ((concept, pred, URIRef(thesaurusAddendum + i)))
                if pred == SKOS.broader:
                    g.add ((URIRef(thesaurusAddendum + i), SKOS.narrower, concept))
            else:
                g.add ((concept, SKOS.topConceptOf, thesaurus))
        else:
            g.add ((concept, pred, URIRef(i))) #urllib.parse.quote(i)
    else:
        if isLang:
            if len(i) > 2 and i[-3] == "@":
                i, baseLanguageLabel = i.split("@")
            g.add ((concept, pred, obj(i, lang= baseLanguageLabel)))
        else:
            g.add ((concept, pred, obj(i)))
    return g

def df2Skos(df, baseLanguageLabel, baseUri, seperator):
    propertyTuples = [
        ("notation", SKOS.notation, Literal, False),
        ("prefLabel", SKOS.prefLabel, Literal, True),
        ("altLabel", SKOS.altLabel, Literal, True),
        ("definition", SKOS.definition, Literal, True),
        ("broader", SKOS.broader, URIRef, False),
        ("narrower", SKOS.narrower, URIRef, False),
        ("related", SKOS.related, URIRef, False),
        ("closeMatch", SKOS.closeMatch, URIRef, False),
        ("relatedMatch", SKOS.relatedMatch, URIRef, False),
        ("exactMatch", SKOS.exactMatch, URIRef, False)
    ]

    DOC = Namespace("http://Restaurierungs-und-Konservierungsdaten.org/doc-vocab#")  # ("https://conservationdata.github.io/docs/")


    extendedTuples = [
        ("source", SKOS.note, Literal, True), #DC.source # False
        #("creator", DC.creator, Literal, False),
        ("seeAlso", RDFS.seeAlso, Literal, False),
        ("Verpflichtungsgrad", DOC.Verpflichtungsgrad, Literal, False),   # SKOS.scopeNote, Literal, True),
        ("translation", SKOS.altLabel, Literal, True),
        ("Feldwert", DOC.TextOrUri, Literal, False), #SKOS.editorialNote, Literal, True), 
        ("Wiederholbar", DOC.Wiederholbar, Literal, False), # SKOS.historyNote, Literal, True),
        ("Empfohlene Vokabulare", DOC.EmpfohleneVokabulare, Literal, False), # SKOS.changeNote, Literal, True),
    ]

    g = Graph()
    thesaurus = URIRef(baseUri)
    thesaurusAddendum = URIRef(thesaurus + "/")

    # use doc as abbreviation for DOC Namespace
    g.bind("doc", DOC)

    g.add ((thesaurus, RDF.type, SKOS.ConceptScheme))
    g.add ((thesaurus, DC.title, Literal("Metadatenvokabular Konservierung/Restaurierung", lang=baseLanguageLabel)))
    g.add ((thesaurus, DC.description, Literal("Sammlung relevanter Metadaten des Faches.", lang=baseLanguageLabel)))
    g.add ((thesaurus, DC.creator, Literal("TWG Standards")))
    #g.add ((thesaurus, DCTERMS.publisher, Literal("Leibniz-Zentrum für Archäologie (LEIZA)")))
    g.add ((thesaurus, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))
    g.add ((thesaurus, DCTERMS.rights, Literal("CC BY 4.0")))
    g.add((thesaurus, VANN.preferredNamespaceUri, Literal(thesaurusAddendum)))

    """
    contributors = ["Kristina Fella", 
                    "Lasse Mempel-Länger", 
                    "Waldemar Muskalla", 
                    "Dr. Ingrid Stelzner", 
                    "Matthias Heinzel",
                    "Christian Eckmann",
                    "Heidrun Hochgesand",
                    "Katja Broschat",
                    "Leslie Pluntke",
                    "Markus Wittköpper",
                    "Marlene Schmucker",
                    "Dr. Roland Schwab",
                    "Rüdiger Lehnert",
                    "Ulrike Lehnert",
                    "Stephan Patscher",
                    "Lena Klar"
                    ]
    for contributor in contributors:
        g.add ((thesaurus, DCTERMS.contributor, Literal(contributor)))
    """

    subjects = ["Konservierung", "Restaurierung", "Metadaten"]

    for subject in subjects:
        g.add ((thesaurus, DCTERMS.subject, Literal(subject, lang=baseLanguageLabel)))

    for index, row in df.iterrows():
        if row["prefLabel"] and isinstance(row["prefLabel"], str) and row["notation"] and isinstance(row["notation"], str):
            #print(row["prefLabel"], row["notation"])
            concept = URIRef(thesaurusAddendum + row['notation'])
            g.add ((concept, RDF.type, SKOS.Concept))
            for prop, pred, obj, isLang in propertyTuples+extendedTuples:
                if prop in df.columns:
                    if not isinstance(row[prop], float):
                        if seperator in row[prop]:
                            seperated = row[prop].split(seperator)
                            langs = [x.split("@") for x in seperated]
                            for i in range(len(seperated)):
                                g = row2Triple(seperated[i], g, concept, pred, obj, isLang, baseLanguageLabel, thesaurusAddendum, thesaurus)
                        else:
                            g = row2Triple(row[prop], g, concept, pred, obj, isLang, baseLanguageLabel, thesaurusAddendum, thesaurus)
            g.add ((concept, SKOS.inScheme, thesaurus))
            if row["broader"] == "top":
                g.add ((thesaurus, SKOS.hasTopConcept, concept))
                g.add ((concept, SKOS.topConceptOf, thesaurus))
    return g

def main(link, baseLanguageLabel, propertyMatchDict, seperator):
    df = csv2Df(link, propertyMatchDict)
    # df = sortNotation(df)
    text = df.to_csv(index=False)
    with open('polishedData.csv', 'w', encoding="utf-8") as f:
        f.write(text)
    df = pd.read_csv('polishedData.csv', encoding="utf-8")
    graph = df2Skos(df, baseLanguageLabel, baseUri, seperator)
    graph.serialize(destination='thesaurus.ttl', format='turtle')   
    #graph.serialize(destination='thesaurus.json-ld', format='json-ld')

link = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRb0tjnjkyjzReZ_--dYJOD4rbl1_iV8EdVTFXATh9ie6u3bRAeEYYrMNKZF0AcM_PQJkQbmZyGFfYe/pub?gid=0&single=true&output=csv"
baseLanguageLabel = "de"
baseUri = "https://www.w3id.org/conservation/terms/metadata" #"https://www.lassemempel.github.io/Restaurierungsdaten/Metadaten"  # "http://data.archaeology.link/terminology/archeologicalconservation"

# dictionary to map divergent column names in the csv to the SKOS properties
propertyMatchDict = {"identifier":"notation","description":"definition","parent":"broader", "note (source)": "source"}
seperator = "|"

main(link, baseLanguageLabel, propertyMatchDict, seperator)