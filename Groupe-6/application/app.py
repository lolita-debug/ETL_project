# SOMMAIRE ---------------------------------------------------------------------------------------------------------------------------------------
# 
# 1. Imports
# 2. Connection à la base de données et dataframes et elements du cyto
# 3. Layout /Mise en page
#       3.1 Définir les STYLES dans des variables
#       3.2 Appliquer les variables dans LAYOUT 
# 4. Callbacks

# ------------------------------------------------------------------------------------------------------------------------------------------------

#_____________________________________________________________  1. IMPORTS  _____________________________________________________________________

import dash
import dash_cytoscape as cyto
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

import plotly.express as px
import plotly.graph_objs as go
import flask

import pandas as pd 
import sqlalchemy

import time
from datetime import datetime
from os import system

#________________________________________________________________________________________________________________________________________________

# Créatoion de la connection et récupération des tables :
engine = sqlalchemy.create_engine("oracle+cx_oracle://stagbi25:Phoenix#Icar67@51.91.76.248:15440/coursdb", max_identifier_length=128)

connection = engine.connect()

query_contraintes = """
    select  
        tbm.TABLE_NAME         as "table_parent",
        clm.COLUMN_NAME        as "col_tab_parent",
        tbe.TABLE_NAME         as "table_enfant",
        cle.COLUMN_NAME        as "col_tab_enfant" 
    from user_constraints tbe 
        join user_cons_columns cle
        on  tbe.TABLE_NAME      = cle.TABLE_NAME
        and tbe.CONSTRAINT_NAME = cle.CONSTRAINT_NAME 
        join user_constraints tbm 
        on tbm.CONSTRAINT_NAME = tbe.R_CONSTRAINT_NAME 
        join user_cons_columns clm
        on  tbm.TABLE_NAME      = clm.TABLE_NAME
        and tbm.CONSTRAINT_NAME = clm.CONSTRAINT_NAME 
    where tbe.CONSTRAINT_TYPE = 'R'
"""

query_tables = """
select 
    table_name, 
    column_name,
    data_type 
from user_tab_columns
"""

# Construction des DataFrames :
df_tab = pd.read_sql_query(query_tables, connection)
df_c = pd.read_sql_query(query_contraintes, connection)

df_c.columns = ['p_table_name', 'p_constraint_name', 'f_table_name', 'f_constraint_name']

df_c_not_reverse = pd.DataFrame()
df_c_not_reverse['p_table_name']=df_c['p_table_name']
df_c_not_reverse['f_table_name']=df_c['f_table_name']

df_c_fkey = pd.DataFrame()
df_c_fkey['p_table_name']=df_c['f_table_name']
df_c_fkey['p_constraint_name']=df_c['f_constraint_name']
df_c_fkey['f_table_name']=df_c['p_table_name']
df_c_fkey['f_constraint_name']=df_c['p_constraint_name']
df_c_fkey = df_c_fkey.sort_values('p_table_name').reset_index(drop=True)
df_c = pd.concat([df_c,df_c_fkey],axis=0).sort_values('p_table_name').drop_duplicates(keep='first').reset_index(drop=True)

df_cyto = pd.DataFrame()
df_cyto['p_table_name']=df_c['p_table_name']
df_cyto['f_table_name']=df_c['f_table_name']
#enlever les lignes quand p_table == f_table
# Supprimer les doublaons 
df_cyto = df_cyto.drop_duplicates(keep='first').reset_index(drop=True)
df_size_node = df_cyto.groupby('p_table_name', as_index=False).agg({'f_table_name':'count'}) #.reset_index()

# Construction des Nodes et des Edges
def elements_cyto(df):
    Elements =[]
    def nodes(tables):
        for nom_table in tables:
            sub_nodes={}
            nodes={}
            sub_nodes['id'] = nom_table
            sub_nodes['label'] =nom_table.title()

            infos_tables = df_tab['column_name'][df_tab['table_name'] == nom_table].values.tolist()
            sub_nodes['infos'] = infos_tables
            sub_nodes['size'] = 10*df_size_node['f_table_name'][df_size_node['p_table_name'] == nom_table].values[0] 
            nodes['data'] = sub_nodes
            Elements.append(nodes)
    nodes(df['p_table_name'].unique())
    nodes(df['f_table_name'].unique())
    
    def source_target(df,reverse=False):
        for val in df.values:
            sub_edges={}
            edges={}
            if reverse==True:
                sub_edges['source'], sub_edges['target']= val[1], val[0]
            else:
                sub_edges['source'], sub_edges['target']= val[0], val[1]
            edges['data'] = sub_edges
            Elements.append(edges)
    source_target(df,reverse=False)
    #source_target(df,reverse=True)
  
    return Elements

list_elements2 =elements_cyto(df_cyto[df_cyto['p_table_name']=='AGENCES'])
list_elements1 =elements_cyto(df_c_not_reverse)

#--------------------------------------------------------------------

# Créatoion de la connection et récupération des tables :
engine = sqlalchemy.create_engine("oracle+cx_oracle://stagbi25:Phoenix#Icar67@51.91.76.248:15440/coursdb", max_identifier_length=128)

connection = engine.connect()
query_ventes ="""
SELECT *
 FROM  COMMANDES COMM
  INNER JOIN  DETAILS_COMMANDES DETA ON COMM.NO_COMMANDE = DETA.NO_COMMANDE
  INNER JOIN  PRODUITS PROD ON DETA.REF_PRODUIT = PROD.REF_PRODUIT
  INNER JOIN  TVA_PRODUIT TVA_ ON PROD.REF_PRODUIT = TVA_.REF_PRODUIT
  FETCH NEXT 10000 ROWS ONLY
"""
df_ventes = pd.read_sql_query(query_ventes, connection)
df_ventes.columns = ['no_commande_pro', 'no_vendeur', 'no_acheteur', 'date_commande',
       'date_envoi', 'livree', 'acquitee', 'annulee', 'no_commande_dcom',
       'ref_produit', 'prix_unitaire', 'quantite_pro', 'port', 'remise',
       'retourne', 'echange', 'ref_produit_pro', 'nom_produit', 'code_categorie',
       'no_fournisseur', 'quantite_cat', 'date_miseajour', 'ref_produit_tva',
       'tva']

df_ventes['date_commande'] = pd.to_datetime(df_ventes['date_commande'])
df_ventes['annee'] = df_ventes['date_commande'].dt.year
df_ventes['mois'] = df_ventes['date_commande'].dt.month
df_ventes['jour'] = df_ventes['date_commande'].dt.day
df_ventes['mois_nom'] = df_ventes['date_commande'].dt.month_name()

df_ventes['CA_commande'] = df_ventes['prix_unitaire'] * df_ventes['quantite_pro']

ca_jour = df_ventes.groupby('date_commande').agg({'CA_commande':'sum'})

clas_prod = df_ventes.groupby(['annee','mois',
                             'nom_produit'], as_index=False).agg({'no_commande_pro':'count'})
clas_prod['classement'] = clas_prod.groupby(['annee','mois'], as_index=False).no_commande_pro.rank(method='dense', ascending=False)
clas_prod = clas_prod.sort_values(['annee','mois', 'classement'], ascending=[1,1,1])


# ________________________________________________  2. CONSTRUCTEUR APPLI + LIENS D INTEGRITE CSS  ______________________________________________


# Liaison automatique vers la Stylesheet du thème SLATE de Boostrap -----------------------------------------------------------------------------

''' 
    Le module 'dash_bootstrap_components.themes' contient des liens vers les feuilles de style Bootstrap et Bootswatch hébergées sur BootstrapCDN.
    La manière la plus simple est d'utiliser l'argument 'external_stylesheets' dans le constructeur 'dash.Dash'.
    Cela Sert à créer facilement un lien vers l'une d'entre elles dans une application. 

'''

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
app.title = '4REQUEST'
# Le fait d'ajouter __name__ dans le constructeur permet de renseigner les métadonnées du doc au navigateur: titre et favicon dans notre cas.
# Pour le favicon, Logo.png a été converti au format '.ico' et inséré dans le fichier 'assets ' sur VS Code car Dash prend automatiquement en compte le dossier assets.
# Attention! Il ne peut y avoir qu un seul fihier 'favicon.ico'!


# Liaison manuelle Stylesheet –––––––––––––––––––––-------------------------------------------------------------––––––––––––––––––––––---––––––– 

    # BS = "https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/slate/bootstrap.min.css"
    # app = dash.Dash(external_stylesheets=[BS])

# _______________________________________________________________________________________________________________________________________________

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# _______________________________________________________________________________________________________________________________________________
# ___________ Feuille de style par défaut pour le cytoscape principal ___________________________
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

default_stylesheet = [
    {
        "selector": 'node',
        'style': {
            "width": "mapData(size, 0, 100, 20, 60)",
            "height": "mapData(size, 0, 100, 20, 60)",
            "opacity": 1,
            "label": "data(label)",
            "label-opacity" : 0.7,
            "color": "white",
            "font-size": 18,
            'z-index': 9999
        }
    },
    {
        "selector": 'edge',
        'style': {
            #"curve-style": "bezier",
            "opacity": 0.5,
            'z-index': 5000
        }
    }
]

# ___________ Feuille de style par défaut pour le 2eme cytoscape ___________________________
default_stylesheet2 = [
    {
        "selector": 'node',
        'style': {
            "opacity": 1,
            "label": "data(label)",
            "label-opacity" : 0.7,
            "color": "white",
            "font-size": 10,
            'z-index': 9999
        }
    },
    {
        "selector": 'edge',
        'style': {
            #"curve-style": "bezier",
            "opacity": 0.5,
            'z-index': 5000
        }
    }
]



# ________________________________________________________________  3. LAYOUT  __________________________________________________________________

# _____________ Fonctions pour la construction des Dropdown ____________

def NamedDropdown(name, **kwargs):
    return html.Div(
        style={'margin': '10px 0px'}, #  La propriété margin définit la taille des marges sur les quatre côtés de l'élément. 
        children=[
            html.P( #html.P le p = paragraphe , attribut html
                children=f'{name}:',
                style={'margin-left': '3px'}
            ),

            dcc.Dropdown(**kwargs)
        ]
    )

def DropdownOptionsList(*args):
    return [{'label': val.capitalize(), 'value': val} for val in args]

def NamedInput(name, **kwargs): 
    return html.Div(
        children=[
            html.P(children=f'{name}:'),
            dcc.Input(**kwargs)
        ]
    )


''' 
3.1 Définir les STYLES dans des variables '''

card_content = [
    dbc.CardHeader("ZOOM"),
    dbc.CardBody(
        [
            cyto.Cytoscape
                        (id='cytoscape2',
                        layout={'name': 'breadthfirst'},
                        stylesheet=default_stylesheet2,
                        style={'width': '100%', 'height': '100%', #"position": "fixed", 
                                                                                # On utilise une position fixe , pas de scroll
},                      #pan = {'x':120,'y':50},

                        zoomingEnabled = False,
                        elements=[] #list_elements2
                        ),
    
        ]
    ),
]

# Sidebar (left) --------------------------------------------------------------------------------------------------------------------------------

SIDEBAR_STYLE = {                                                                # Création du style pour la barre latérale
    "position": "fixed",                                                         # On utilise une position fixe , pas de scroll
    "top": 0,                                                                    # annule le padding navigateur et commence à 0
    "left": 0,
    "bottom": 0,
    "width": "26rem",                                                            # taille/largeur 
    "padding": "2rem 1rem",
    "background-color": "#095860",# 043a3f 144856, 003338 055a63                 # test couleurs fond sidebar gauche
}

CONTENT_STYLE = {                                                               # the styles for the main content position it to the right of the sidebar and                                                                         
    "margin-left": "18rem",                                                     # add some padding.
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [   html.Div(html.Img(src=app.get_asset_url('LOGO_4REQUEST.png'))),    #Import du logo depuis assets
        #html.H2("4REQUEST", className="display-4", style= {"font-family": "Arial",'font-size': 54}),
        html.Hr(),
        html.Br(),
        html.Br(),
        html.P(
            "Select a node from the graph to generate a SQL querry which will be displayed in the querry section. Additionally, you can custmize the design of the graph with the options on the left sidebar", className="lead", style={"font-family": "Calibri","font-size":20, "text-align": "justify"}
        ),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Div([
            dbc.Row(
                dbc.Col([
    html.P("Graph's Style :"),                
    dcc.Dropdown(
        id='Select_cyto_type',
        options=[
        {'label': 'Breadthfirst', 'value': 'breadthfirst'},
        {'label': 'Grid', 'value': 'grid'},
        {'label': 'Circle', 'value': 'circle'},
        {'label': 'Concentric', 'value': 'concentric'},
        {'label': 'Cose', 'value': 'cose'} 
        ],
        value='breadthfirst', 
        style={'width': '100%', 'background-color': 'F54C08'}
        ),
        html.Hr(),
        html.P("Points' Style :"),
    dcc.Dropdown(
        id='dropdown-node-shape',
        style={'width': '100%', 'background-color': 'F54C08'},
        value='ellipse',
        clearable=False,
        options=DropdownOptionsList(
                        'ellipse',
                        'triangle',
                        'rectangle',
                        'diamond',
                        'pentagon',
                        'hexagon',
                        'heptagon',
                        'octagon',
                        'star',
                        'polygon',
                    )),
    html.Hr(),
    NamedInput(
        name='Followers Color',
        id='input-follower-color',
        type='text',
        value='#00826f',#vert
        style={'width': '100%', 'background-color': 'F54C08','justifyContent':'center'} 
        #value='#0074D9',
            ),
    html.Hr(),
    NamedInput(
        name='Following Color',
        id='input-following-color',
        type='text',
        value='#01d6d9',#bleu 
        style={'width': '100%', 'background-color': '#fffffe','justifyContent':'center'}
            ),
    

                    ])
                ),
            html.Div(id='dd-output-container')
        ]),
                
        dbc.Nav(
            [
                

            ],
            vertical=True,
            pills=True,
        ),

        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
    
        

        html.Footer("© 2020 HOLA Organization", 
        style={'textAlign': 'center', 
               #'background': '#45a1ff',
               'text': '#7FDBFF'
               }
        # justify-content: center;
         #padding: 5px;
         #background-color: #45a1ff;
         #color: #fff;
        # 
        # style = display: flex;        
        ),

    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)


################################################################################################
# CONSTRUCTION DES CYTOSCAPES METIER : VENTES, COMMISSIONNEMENT, STOCK ET FACTURES
def df_stars(*arg):
    liste_t = [i.upper() for i in arg]
    df_star = pd.DataFrame()
    for i in liste_t:
        for j in liste_t:
            df = df_cyto[(df_cyto['p_table_name'] == i) & (df_cyto['f_table_name'] == j)] 
            if not df.empty:
                df_star = pd.concat([df_star, df], axis=0)
    if df_star.empty:
        print("Il n'y a pas de relations entre ces tables")
        print(liste_t)
    return df_star.reset_index(drop=True)


list_elements_ventes=elements_cyto(df_stars('COMMANDES', 'DETAILS_COMMANDES','produits','TVA_PRODUIT'))
list_elements_factures=elements_cyto(df_stars('FACTURES', 'RELANCES', 'commandes'))
list_elements_commissions=elements_cyto(df_stars('agences','vendeurs', 'COMMISSIONNEMENTS', 'COMMISSIONNEMENTS_AGENCES', 'COMMISSIONNEMENTS_VENDEURS'))
list_elements_stock=elements_cyto(df_stars('STOCKS_ENTREPOTS', 'Produits', 'mouvements', 'agences', 'GESTIONS_STOCKS'))


sidebar_ventes = html.Div(
    [
        html.Div(html.Img(src=app.get_asset_url('LOGO_4REQUEST.png'))),
        #html.H2("4REQUEST", className="display-4"),
        #html.Div(html.Img(src=app.get_asset_url('LOGO_2.png'), height=90)),     #import du logo depuis fichier assets
        html.Hr(),
        html.Br(),
        html.P(
            "Analysis of the turnover and study of the last three months sells with the aim of planning the forecast budget and the annual general assembly", className="lead", 
        style={"font-family": "Calibri","font-size":20, "text-align": "justify"}),
        html.Br(),
        html.Br(),
        html.Br(),

        html.Div(children=[
                    html.Div(className='col', children=[
                        dcc.Dropdown(id='annee-dd', 
                        value=2019, 
                        options=[{"label":"2019", "value":2019}]),

                        html.Br(),

                        dcc.Dropdown(id='mois-dd', 
                        value=10, 
                        options=[{"label":"Oct", "value":10},
                                {"label":"Nov", "value":11},
                                {"label":"Dec", "value":12}])
                        ])]), 

        html.Br(),

        html.Div([
            cyto.Cytoscape(
                id='cytoscape-ventes',
                layout={'name': 'breadthfirst'},
                style={'width': '100%', 'height': '800px'},
                stylesheet=default_stylesheet2,
                elements=list_elements_ventes #list_elements2
            )]),

        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(), 
        html.Br(),
        html.Br(), 
        html.Br(),
        html.Br(), 
        html.Br(),
        html.Br(),

        html.Footer("© 2020 HOLA Organization", 
        style={'textAlign': 'center', 
               #'background': '#45a1ff',
               'text': '#7FDBFF'
               }
             
        ),

    ],
    style=SIDEBAR_STYLE,
)

content_ventes = html.Div(id="page-content_ventes", style=CONTENT_STYLE)

##############################################################################################""

# Sidebar (right) --------------------------------------------------------------------

SIDEBAR_STYLE_RIGHT = {                                                          # Création du style pour la barre latérale droite
    "position": "fixed",                                                         # On utilise une position fixe 
    "top": 0,
    "right": 10,
    "bottom": 0,
    "width": "26rem",                                                            # On utilise une largeur fixe 
    "padding": "2rem 1rem",
    "background-color": "transaparent",
}

                                                                                # the styles for the main content position it to the right of the sidebar and
                                                                                # add some padding.
#CONTENT_STYLE_RIGHT= {
    #"margin-left": "2rem",
    #"margin-right": "18rem",
    #"padding": "2rem 1rem",
#}
sidebar_RIGHT_ventes = html.Div([
       
        #html.Div(html.Img(src=app.get_asset_url('LOGO_2.png'), height=90)),     #import du logo depuis fichier assets
        #html.Hr(),
        html.Br(),
        html.Br(),
        html.Br(),  

        
        html.Br(),
        html.Br(),
        html.Br(),
        
        

        html.Br(),
       
        

        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),

    ],
    style=SIDEBAR_STYLE_RIGHT,
)

content_RIGHT_ventes = html.Div(id="page-content_right_ventes")

sidebar_RIGHT= html.Div(
    [   
        dbc.Card(card_content, color="dark", outline=True, style= {"height":250}),
        html.Br(),
        html.P(
            " Click on the following buttons to execute, save, reinitialize or check the history", className="lead", 
        ),
        
        dbc.Nav(
            [
                 html.Br(),
                 dbc.Button(
                    "EXECUTE",
                    color="primary",
                    block=True,
                    id='execution-requete',
                    className="mb-3"),

                    #Création du bouton SAVE 
                dbc.Button(
                    "SAVE",
                    color="primary",
                    block=True,
                    id='button-sauvegarde',
                    className="mb-3"),

                dbc.Button(
                    "HISTORY",
                    color="primary",
                    block=True,
                    id='hist-requetes',
                    className="mb-3"),

                dbc.Button(
                    "RESET",
                    color="secondary",
                    block=True,
                    id='button-reset',
                    className="mb-3"),

                html.Br(),
                html.Br(),
                html.Br(),
                
                dbc.Button(
                    "Request Infos",
                    color="primary",
                    block=True,
                    id="button_submit",
                    className="mb-3"),

                html.Div(id='container-button-timestamp'),
                #html.Button('Submit', id='textarea-state-example-button', n_clicks=0),
                html.Div(id='textarea-state-example-output', style={'whiteSpace': 'pre-line'})

               
            ],
            vertical=True,
            pills=True,
        ),

        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),

    ],
    style=SIDEBAR_STYLE_RIGHT,
)

content_RIGHT = html.Div(id="page-content_right")#, #style=CONTENT_STYLE_RIGHT



# PAGE GRAPH (PRINCIPALE) ------------------------------------------------------------------------------

loader = html.Div(children=[ 
    dbc.Container(      
                                                      # Création mise en page
    [ 
    html.Br(),
    cyto.Cytoscape(
        id='graphique_cyto',
        layout={'name': 'breadthfirst'},
        stylesheet=default_stylesheet,
        style={'width': '100%', 'height': '600px'},
        #pan = {'x':120},
        #zoom = 0.7,
        #zoomingEnabled = False,
        elements=list_elements1
                ),

    # LAYOUT CHECKLIST CHOIX DES COLONNES
    # dbc.Row([

    #         dbc.Checklist(
    #         id='checklist-colonnes',
    #         options=[],
    #         value = [],
    #         # inline= True,
    #         # labelCheckedStyle= 
            
    #         #style = {'rotation': 90}

    #         inputStyle={"vertical-align":"middle", "margin":"auto"},
    #         labelStyle={"vertical-align":"middle"},
    #         style={"display":"inline-flex", "flex-wrap":"wrap", "justify-content":"space-between","line-height":"28px"}
    #     ),
    # ]),

dbc.FormGroup(
    [
        
        dbc.Checklist(
            options=[
            ],
            value=[],
            id="checklist-colonnes",
            inline=True,
        ),
    ]
),


    html.Br(),
        dbc.Row([
            dbc.Col(
                html.Pre(
        id='cytoscape-mouseoverNodeData-json', 
        style=styles['pre']
                    )
    ),



            dbc.Col(
    dcc.Textarea(
        id='request_data',
        value='Visualise your querry',
        style={'width': '100%', 'height': 200},
                ))
                ]),                                                     
        
        html.Div([dcc.Location(id="url"), sidebar, content]),

        html.Div([dcc.Location(id="page-content_right"), sidebar_RIGHT#, CONTENT_STYLE_RIGHT
        ]),
        ])
])


# PAGE VENTES -------------------------------------------------------------------------------------------------------------------------------------

page_ventes = html.Div(children=[
    dbc.Container([
       
            html.Br(),
            dcc.Graph(id='graphe1', figure={
                                           'layout':go.Layout(                               #Appliquer un style personnalisé au graph 1     
                                            title = 'Le CA dans le mois', 
                                            # paper_bgcolor = 'rgba(0,0,0,0)',                # couleur du fond de l espace graphique
                                            # plot_bgcolor = 'rgba(0,0,0,0)',                 # couleur du fond du graph
                                            font=dict(color="#00d3d3", size=10),
                                            )
                                            }
            ),
            html.Br(),
            html.Br(),
            dbc.Row([
                    dbc.Col(
                        dcc.Graph(id='graphe2',  figure={'layout':go.Layout( 
                                                        title = 'Les cinq produits les plus vendus', 
                                                        # paper_bgcolor = 'rgba(0,0,0,0)', 
                                                        # plot_bgcolor = 'rgba(0,0,0,0)'
                                                        font=dict(color="#00d3d3", size=10),
                                                        #width= 550
                                                        )})),
                    
                    dbc.Col(width=50),
                    dbc.Col(
                        dcc.Graph(id='graphe3', figure={'layout':go.Layout( 
                                                        title = 'Les cinq produits les moins vendus', 
                                                        # paper_bgcolor = 'rgba(0,0,0,0)', 
                                                        # plot_bgcolor = 'rgba(0,0,0,0)' 
                                                        font=dict(color="#00d3d3", size=10),
                                                        #width= 550
                            )})
                        ),
                    ],
            ),
]
),
    html.Div([ sidebar_ventes, content_ventes]),
    html.Div([ sidebar_RIGHT_ventes])])


# Callbacks des graphes métier : onglet : ventes 

@app.callback(Output('graphe1', 'figure'),
              [Input('annee-dd', 'value'),
              Input('mois-dd', 'value')])

def selectDateGraph1(annee, mois):
    date = str(annee)+'-'+str(mois)
    ca_jour_am = ca_jour[date]
    return px.line(ca_jour_am.reset_index(), x='date_commande', y='CA_commande', 
                                            color_discrete_map={
                                                "CA_Commande": "yellow"}, 
                                            labels={'date_commande': "Month", 'CA_commande': "Turnover"},
                                            width= 1096,
                                            template = "plotly_dark" 

            ) 

@app.callback(Output('graphe2', 'figure'),
              [Input('annee-dd', 'value'),
              Input('mois-dd', 'value')])

def selectDateGraph2(annee, mois):
    df = clas_prod[(clas_prod['annee']==annee) & (clas_prod['mois']==mois)].head(5)
    return px.bar(df, x='nom_produit', y='no_commande_pro', 
                        
                                            color_discrete_map={
                                                "no_commande_pro": "yellow"}, 
                                            labels={'nom_produit': "Products", 'no_commande_pro': "Top five sellers"},
                                            width= 540,
                                            template = "plotly_dark"  )


@app.callback(Output('graphe3', 'figure'),
              [Input('annee-dd', 'value'),
              Input('mois-dd', 'value')])

def selectDateGraph3(annee, mois):
    df = clas_prod[(clas_prod['annee']==int(annee)) & (clas_prod['mois']==int(mois))].tail(5)
    return px.bar(df, x='nom_produit', y='no_commande_pro', 
                        color_discrete_map={
                                                "no_commande_pro": "yellow"}, 
                                            labels={'nom_produit': "Products", 'no_commande_pro': "The five worst sales"},
                                            width= 540,
                                            template = "plotly_dark" 
     )


# PAGE STOCK ---------------------------------------------------------------------------------------------------------------------------------------------

page_stock = html.Div(id="page-content-loader",children=[
    dbc.Container([
        html.Br(),
        html.Br(),
        dbc.Tabs(
            [
                dbc.Tab(label="Database", tab_id="graph"),
                dbc.Tab(label="Sales", tab_id="ventes"),
                #dbc.Tab(label="Commandes", tab_id="Commandes"),
                dbc.Tab(label="Stock", tab_id="stock"),
                dbc.Tab(label="Billing", tab_id="facturation"),
                dbc.Tab(label="Commissioning", tab_id="commissionnement")
            ],
            id="tabs",
            active_tab="stock",
        ),

        
    html.Div([dcc.Location(id="url"), sidebar_ventes, content_ventes]),
    html.Div([dcc.Location(id="page-content_right_ventes"), sidebar_RIGHT_ventes]),
    ]),])
# PAGE STOCK ---------------------------------------------------------------------------------------------------------------------------------------------

page_stock = html.Div(children=[
    dbc.Container([
        cyto.Cytoscape(
        id='cytoscape-stock',
        layout={'name': 'breadthfirst'},
        style={'width': '100%', 'height': '400px'},
        stylesheet=default_stylesheet2,
        elements=list_elements_stock #list_elements2
    ),

    #html.Div([sidebar_ventes, content_ventes]),
    #html.Div([sidebar_RIGHT_ventes]),
    ]),])

# PAGE FACTURE ---------------------------------------------------------------------------------------------------------------------------------------------

page_facture = html.Div(children=[
    dbc.Container([
        cyto.Cytoscape(
        id='cytoscape-factures',
        layout={'name': 'breadthfirst'},
        style={'width': '100%', 'height': '400px'},
        stylesheet=default_stylesheet2,
        elements=list_elements_factures #list_elements2
    ), 
    #html.Div([sidebar_ventes, content_ventes]),
    #html.Div([sidebar_RIGHT_ventes]),
    ]),])

# PAGE COMMISSION ---------------------------------------------------------------------------------------------------------------------------------------------

page_commissionnement = html.Div(children=[
    dbc.Container([
    #html.Div([sidebar_ventes, content_ventes]),
    #html.Div([sidebar_RIGHT_ventes]),

    cyto.Cytoscape(
        id='cytoscape-commissionnements',
        layout={'name': 'breadthfirst'},
        style={'width': '100%', 'height': '400px'},
        stylesheet=default_stylesheet2,
        elements=list_elements_commissions #list_elements2
    ),


    ]),])


# validate ALL layouts (obsolète avec tab(children=[])) ------------------------------------------------------------------------------------------------------------------------------------
"""
app.validation_layout = html.Div([
    loader,
    page_ventes,
    page_stock,
    page_facture,
    page_commissionnement
])
"""

# -------------------------------------------------------------------------------------------------------------------------------------

app.layout = html.Div(
    dbc.Container([
        html.Br(),
        html.Br(),
        dbc.Tabs(
            [
                dbc.Tab(label="Database", tab_id="graph",children=[loader]),
                dbc.Tab(label="Sales", tab_id="ventes",children=[page_ventes]),
                #dbc.Tab(label="Commandes", tab_id="Commandes",children=[page_Commandes]),
                dbc.Tab(label="Stock", tab_id="stock",children=[page_stock]),
                dbc.Tab(label="Billing", tab_id="facturation",children=[page_facture]),
                dbc.Tab(label="Commissioning", tab_id="commissionnement",children=[page_commissionnement])
            ],
            id="tabs",
            active_tab="graph",
        ),
        ]))

# ___________________________________________________________  4. CALLBACKS ___________________________________________________________



# Afficher les colonnes des différentes tables au survol avec la souris 

@app.callback(Output('cytoscape-mouseoverNodeData-json', 'children'),
              [Input('graphique_cyto', 'mouseoverNodeData')])
def displayTableInfos(Data):
    if Data==None:
        return "Positionate yourself on a node to visualise the table's columns."
    else:    
        infos_tables = '|_________ Les colonnes de la table : '+'{:^24}'.format(Data['id'])+' ________|'+'\n'
        for index, col in enumerate(df_tab[['column_name', 'data_type']][df_tab['table_name'] == Data['id']].values):
            infos_tables +='| La colonne n° {} : {:<24} | Type Data : {}'.format(index+1, col[0], col[1])+'\n'
        return infos_tables




# CHOIX DU TYPE DE GRAPHE : Preset, Random, Grid, Circle, Concentric, Breadthfirst,Cose
# :
@app.callback(Output('graphique_cyto', 'layout'),
              [Input('Select_cyto_type', 'value')])
def selectCytoType(value):
    return {'name': value}


# GESTION DE LA FEUILLE "STYLESHEET" DE STYLE POUR LE CYTO EN FONCTION DES ACTIONS DE L'UTILSATEUR
# :
@app.callback(Output('graphique_cyto', 'stylesheet'),
              [Input('graphique_cyto', 'tapNode'),
               Input('input-follower-color', 'value'),
               Input('input-following-color', 'value'),
               Input('dropdown-node-shape', 'value'),
               Input('button-reset', 'n_clicks')])
def generate_stylesheet(node, follower_color, following_color, node_shape, reset_button):
    if not node:
        return default_stylesheet

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if "button-reset" in changed_id:
        return default_stylesheet

    # NOUVELLE STYLESHEET PAR DESSUS LA DEFAULT
    stylesheet = [{
        "selector": 'node',
        'style': {
            "width": "mapData(size, 0, 100, 20, 60)",
            "height": "mapData(size, 0, 100, 20, 60)",
            'opacity': 0.3,
            'shape': node_shape,
        }
    }, {
        'selector': 'edge',
        'style': {
            'opacity': 0.2,
            #"curve-style": "bezier",
        }
    }, {
        "selector": 'node[id = "{}"]'.format(node['data']['id']),
        "style": {
            'background-color': "#00826f", # '#B10DC9',
            "border-color": "white",# "purple",
            "border-width": 2,
            "border-opacity": 1,
            "opacity": 1,

            "label": "data(label)",
            "color": "white",
            "text-opacity": 1,
            "font-size": 18,
            'z-index': 9999
        }
    }]

    for edge in node['edgesData']:
        if edge['source'] == node['data']['id']:
            stylesheet.append({
                "selector": 'node[id = "{}"]'.format(edge['target']),
                "style": {
                    'background-color': following_color,
                    "label": "data(label)",
                    "color": following_color,
                    'opacity': 0.9
                }
            })
            stylesheet.append({
                "selector": 'edge[id= "{}"]'.format(edge['id']),
                "style": {
                    "mid-target-arrow-color": following_color,
                    "mid-target-arrow-shape": "vee",
                    "line-color": following_color,
                    'opacity': 0.9,
                    'z-index': 5000
                }
            })

        if edge['target'] == node['data']['id']:
            stylesheet.append({
                "selector": 'node[id = "{}"]'.format(edge['source']),
                "style": {
                    'background-color': follower_color,
                    "label": "data(label)",
                    "color": follower_color,
                    'opacity': 0.9,
                    'z-index': 9999
                }
            })
            stylesheet.append({
                "selector": 'edge[id= "{}"]'.format(edge['id']),
                "style": {
                    "mid-target-arrow-color": follower_color,
                    "mid-target-arrow-shape": "vee",
                    "line-color": follower_color,
                    'opacity': 0.9,
                    'z-index': 9999
                }
            })
    # TOUS LES NODES SELECTIONNES AURONT UNE MEME COULEUR 
    for node in liste_tables:
        stylesheet.append({
            "selector": 'node[id= "{}"]'.format(node),
            "style": {
            'background-color': "#095860",
            'opacity': 1,
            "label": "data(label)",
            "label-opacity" : 1,
            "font-size": 14,
            "color": "#095860",
            'z-index': 9999
            }
            })
    
    # LES NODES EN CONNECTION (POSSIBILITE DE CREER UNE JOINTURE) AVEC LES NODES DEJA SELECTIONNES  
    # SERONT ECLAIRES POUR INDIQUER A L'UTILISATEUR QU'IL PEUT LES SELECTIONNER
    tables_targets = []
    for i in [(df_c['f_table_name'][df_c['p_table_name']==table].values) for table in liste_tables]:
        for j in i:
            tables_targets.append(j)

    for node in tables_targets:

        stylesheet.append({
            "selector": 'node[id= "{}"]'.format(node),
            "style": {
            'opacity': 1,
            "border-color": "white",# "purple",
            "border-width": 2,
            "border-opacity": 1,
            "label": "data(label)",
            "label-opacity" : 1,
            "font-size": 14,
            "color": "white",
            'z-index': 3000
            }
            })

    return stylesheet

# DES QUE L'UTILISATEUR SELECTIONNE UN NODE DANS LE CYTO PRINCIPAL
# UN SECOND CYTO CONSTRUIT A PARTIR DE LA TABLE EN QUESTION ET SES CONNECTIONS SERA TRACE
# :
@app.callback(Output('cytoscape2', 'elements'),
              [Input('graphique_cyto', 'tapNodeData')],
              [State('cytoscape2', 'elements')])

def cb2(tapNodeData, elements):
    if tapNodeData:
        data= tapNodeData['id']

        return elements_cyto(df_cyto[df_cyto['p_table_name']==data])
    else:
        return elements

# CHECKLIST : A LA SELECTION D'UNE TABLE (NODE) LES COLONNES ASSOCIEES A LA TABLE SONT ENVOYEES 
# A LA CHECKLIST ET LES VALEURS COCHES AUSSI SONT RECUPEREES
# SI LE BOUTON RESET EST ENCLENCHE LA CHECKLIST SE REINITIALISE

@app.callback([Output('checklist-colonnes', 'options'), 
               Output('checklist-colonnes', 'value')],
              [Input('graphique_cyto', 'tapNode'), 
               Input('button-reset', 'n_clicks')],
              [State('checklist-colonnes', 'value')])
def checklicstColunms(Data, click, valueS):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if (Data==None) or ("button-reset" in changed_id):
        options=[]
        value=[]
        return (options, value)

    else:
        options = []
        for i in Data['data']['infos']:
            dict_labels = {}
            dict_labels["label"] = i.title()
            dict_labels["value"] = Data['data']['id'].lower()+'.'+i
            options.append(dict_labels)
        return (options, valueS)

#___________________________________________________________



#  GESTION DES BOUTONS ET DU MESSAGE A AFFICHER
@app.callback(Output('container-button-timestamp', 'children'),
             [Input('button-sauvegarde', 'n_clicks'),
             Input('hist-requetes', 'n_clicks'),
             Input('execution-requete', 'n_clicks')])

def buttons(n_clicks_sauv, n_clicks_hist, n_clicks_exe):
    if len(liste_tables) == 0:
        msg = "The querry is empty. Please select a node"
    else:
        msg = 'Requête en cours...'
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
        if ('button-sauvegarde' in changed_id):
            with open(r'./Historique_des_requetes.txt', 'a') as file:
                ligne_ajouter = "***********************************************************************************" + '\n' \
                               +"**********            La date : "+ str(datetime.now())+ "              **********" +'\n'\
                               +"************************************ La requête ***********************************" + '\n' \
                               + requete + '\n'\
                               +"***********************************************************************************" + '\n'
                file.write(ligne_ajouter)
            msg = 'The querry has been save'
        
        elif 'execution-requete' in changed_id:
            fichier_tables = 'JointureTables'
            for i in liste_tables:
                fichier_tables += '_' + i[:4]
            # POUR EXECUTER LA REQUETE DECOMMENEZ LES LIGNES SUIVANTES :
            #df_exe = pd.read_sql_query(requete, connection)
            #df_exe.to_parquet(fichier_tables+'.parquet.gzip', compression='gzip')

            msg = 'The querry has been correctly executed and has been saved as __: '+fichier_tables+'.parquet.gzip'
        
        elif 'hist-requetes' in changed_id:
            msg = "Queries'history"
            fichier_lire = "start notepad " +'Historique_des_requetes.txt'
            system(fichier_lire)    
    
    return html.Div(msg)


# CONSTRUCTION DE LA REQUETE : CALLBACK PRINCIPAL
# La requete est construite au fur et à mesure des actions de l'utilisateur. Elle est alimentée par
# Les tables et les colonnes sélectionnées, elle peut être réinitialiser
# Une approche POO est plus intéressante mais dans cette version de l'appli, nous avons utilisé 
# des variable globales : requete <= le corps de la requete en construction
#                       : liste_tables <= une liste des tables sélecionnées 
# le resetButton a été ajouté pour gérer un bug au niveau du boutton reset-button et en principe il doit être enlever  

# Explication du fonctionnement :
# Le output est 'request_data' (un TextArea qui permet l'affichage de la requete)
# On a besoin de récupérer les différentes nodes sélectionnés et qui seront ajouter à liste_tables
# On a besoin des colonnes sélectionnées à partir de la checklist
# Un bouton reset pour effacer la requete et la liste des nodes sélectionnés : requete et liste_tables

requete =''    
liste_tables = [] 
resetButton =0

@app.callback(Output('request_data', 'value'),
            [Input('graphique_cyto', 'tapNode'),
             Input('button-reset', 'n_clicks'),
             Input('checklist-colonnes', 'value')], 
             [State('button-reset', 'n_clicks')])

def display_request(NodeData, colonnes, col_list, clicksS):
    global requete
    global liste_tables
    global resetButton  # pour gérer un bug !!

    # REINITIALISATION AVEC LE BOUTON 'button-reset'
    if (resetButton != clicksS) and (clicksS != None):
        requete = ''
        liste_tables = []
        resetButton = clicksS
        return "Choose a table by selecting a node on the graph"

    if not NodeData:
        requete = ''
        liste_tables = []
        return "Choose a table by selecting a node on the graph"
    else:
        # CONSTRUCTION DU SELECT POUR LE PREMIER NODE SELECTIONNE
        NodeTable = NodeData['data']['id']
        if len(liste_tables) == 0:
            liste_tables.append(NodeTable)
            alias = NodeTable.lower()
            requete += "SELECT  * "+ "\n" " FROM  " +  NodeTable+" " + alias  + "\n"
        else:
            # A PARTIR DU 2EME NODE ON DOIT AJOUTER LE INNER JOIN

            # CONSTRUCTION D'UNE TABLE CONTENANT TOUTES LES CONNECTIONS AVEC LES TABLES SELECTIONNEES
            # CE CHOIX A ETE FAIT AVANT DE DECOUVRIR LES PROPRIETES DU tapNode ET DONC ON RECONSTRUIT 
            # AVEC LES DATAFRAMES TOUTES LES CONNECTIONS
            tables_targets = []
            for i in [(df_c['f_table_name'][df_c['p_table_name']==table].values) for table in liste_tables]:
                for j in i:
                    tables_targets.append(j)

            # LE N-EME NODE PEUT ETRE DANS TROIS CATEGORIES :
            # 1- UN NODE DEJA SELECTIONNE (NodeTable in liste_tables)-> ON FAIT RIEN
            # 2- UN NODE AVEC UNE CONNNECTION POSSIBLE (NodeTable in tables_targets)-> ON L'AJOUTE A LA REQUETE
            # 3- UN NODE AVEC AUCUNE CONNECTION (ELSE) -> ON FAIT RIEN
            if NodeTable in liste_tables:
                requete = requete

            elif (NodeTable in tables_targets):
                index_parent = -1
                
                if NodeTable not in liste_tables:
                    index_parent = -2
                    liste_tables.append(NodeTable)
                    
                    # RECHERCHE D'UNE CONNECTION ENTRE LA TABLE SELECTIONNEE  
                    # ET UNE TABLE DANS LA LISTE DE TABLES DEJA SELECTIONNEES
                    if NodeTable not in df_c['f_table_name'][df_c['p_table_name']==liste_tables[index_parent]].values:
                        for i in liste_tables[:-1]:
                            pk = df_c['p_constraint_name'][(df_c['p_table_name']==i) & (df_c['f_table_name']==NodeTable)].values
                            if len(pk) != 0:
                                index_parent = liste_tables.index(i)
                                break

                index_enfant = liste_tables.index(NodeTable)

                pk = df_c['p_constraint_name'][(df_c['p_table_name']==liste_tables[index_parent]) & (df_c['f_table_name']==liste_tables[index_enfant])].values
                fk = df_c['f_constraint_name'][(df_c['p_table_name']==liste_tables[index_parent]) & (df_c['f_table_name']==liste_tables[index_enfant])].values

                palias = liste_tables[index_parent].lower()
                falias = liste_tables[index_enfant].lower()

                requete += '  INNER JOIN  ' + NodeTable + " " + falias + '\n'\
                    +'      '+" ON " + palias + "." + pk[0] +" = "+ falias + "." + fk[0] + "\n"

            else:
                requete = requete
    # APRES LA CONSTRUCTION DE LA REQUETE AVEC LES TABLES ON LUI AJOUTE  
    # LES COLONNES SELECTIONNES POUR CHAQUE TABLE 
    # :    
    # ETAPE 1 ON CONSTRUIT LES COLONNES DANS UNE STRING LIGNE APRES LIGNE
    # IMPORTANT : LES COLONNES ONT DEJA L'ALIAS DE LEURS TABLES RESPECTIVES

    if (col_list != []) and (col_list != None):
        req_colonnes = ''
        for col in col_list:
            req_colonnes += '      ' + col +','+"\n"

    # ETAPE 2 ON SPLIT LA REQUETE AU NIVEAU DU FROM ON AJOUTE LA PARTIE COLONNES A LA FIN 
    # ET ON RECONTRUIT LA REQUETE
        split_requete = requete.split('FROM')
        requete = "SELECT  "+ "\n" + req_colonnes[:-2] + "\n" \
            + "FROM" + split_requete[1]
    return requete

# _________________________________________________________________________________________________________________________________

print('run')


# __________________________________________________  6. DEBUG   __________________________________________________________________

if __name__ == "__main__":
    app.run_server(debug=True, use_reloader= True )