# Imports
import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output    # State
import plotly.graph_objs as go
import cufflinks as cf

import numpy as np
import pandas as pd
from datetime import datetime
# import json   for displaying hoverdata
import base64  # for displaying logo/image without online hosting


# simple authentication
# - can use Plotly/Dash OAuth services for better protection
USERNAME_PASSWORD_PAIRS = [
    ['Demo', 'demo']
]

# Read in data
df = pd.read_excel('DashboardDemo_RandomData.xlsx',
                   sheet_name='Data', parse_dates=['Month'])
sf = pd.read_excel('DashboardDemo_RandomData.xlsx', sheet_name='SF_Rates')

# Calculate extra cols:
# eg. Service Fee, Commission paid,
# and recalculate margin from just Sales and Commission

# Lookup the month and use the consultant rates at that time to calculate SF,
# if none, use month appropriate Default values


def service_fee_calc(row):
    name = row['Consultant']
    date = row['Month']
    filtered_sf = sf[sf['Date_applied'] <= date]

    if name in filtered_sf['Consultant'].values:
        # use most recent from before this date
        vals = filtered_sf[filtered_sf['Consultant'] == name].iloc[-1]
    else:
        # else use most recent default from before this date
        vals = filtered_sf[filtered_sf['Consultant'] == 'DEFAULT'].iloc[-1]
    return vals['SF_flat'] + vals['SF_pct'] * row['Commission'] / 100


def margin_divide(df):
    return None if df['Gross sales'] == 0 \
        else 100 * df['Commission'] / df['Gross sales']


def financial_year(date):
    if date.month >= 7:
        return f'{date.year}.{date.year+1}'
    else:
        return f'{date.year-1}.{date.year}'


df['Service fee'] = df.apply(service_fee_calc, axis=1)
df['Commission paid'] = df['Commission'] - df['Service fee']
df['Month_label'] = df['Month'].apply(lambda x: datetime.strftime(x, "%b %Y"))
df['Margin'] = df[['Commission', 'Gross sales']].apply(margin_divide, axis=1)
df['Financial_year'] = df['Month'].apply(financial_year)


# Rounding values for ease of reading.
# nb. Values will be very slightly off due to rounding. Deemed acceptable
df = df.round({
    'Gross sales': 0,
    'Cost of sales': 0,
    'Commission': 0,
    'Service fee': 0,
    'Commission paid': 0,
    'Margin': 1
})

# calculate some useful values/lists
months = list(df['Month_label'].unique())  # month labels
months_dt = list(df['Month'].unique())  # month datetimes
num_of_months = len(months)
years = df['Month'].apply(lambda x: datetime.strftime(x, "%Y")).unique()
fin_years = df['Financial_year'].unique()
consultants = np.sort(df['Consultant'].unique())
top5_selected = None  # global variable needed later
max_prev_years = 5  # for graph 7, comparing previous years for consultant

# for ease of altering if necessary
cols_to_graph_1 = ['Gross sales', 'Commission', 'Service fee']
cols_to_graph_4 = ['Gross sales', 'Commission', 'Service fee']
cols_to_graph_5 = ['Service fee', 'Commission paid', 'Cost of sales']
cols_to_graph_6 = ['Gross sales', 'Commission', 'Service fee']
cols_to_graph_7 = ['Gross sales', 'Commission', 'Service fee']

in_date_overall_margin = round(
    100 * df['Commission'].sum() / df['Gross sales'].sum(), 1)

colour_list = [
 'rgb(215,25,28)',
 'rgb(253,174,97)',
 'rgb(255,255,50)',
 'rgb(171,217,233)',
 'rgb(44,123,182)'
 ]

# Reshape the data.
# Columns=['Month', 'Consultant', 'Gross sales', 'Cost of sales', 'Commission',
# 'Margin', 'Service fee', 'Commission paid', 'Month_label', 'Financial_year']
cols_of_interest = df.columns[2:]
df_reshaped = df.pivot_table(
    index='Month', columns='Consultant', values=cols_of_interest)
df_in_date = df[(df.Month >= months_dt[-12]) & (df.Month <= months_dt[-1])]
df_in_date_reshaped = df_in_date.pivot_table(
    index='Month', columns='Consultant', values=cols_of_interest)


# Visualisations

# 1 Line graph - Sales/Commission/Service Fee vs time


fig1 = df_in_date_reshaped['Gross sales'].iplot(
    title='Gross sales', asFigure=True)
fig1['layout'].update({'hovermode': 'closest'})

gr1_line = dcc.Graph(
    id='gr1',
    figure=fig1,
    style={'height': '80vh'}
)

# 2 - Margin history - updated  to individual consultant on gr1 hover
fig2 = df_in_date_reshaped['Margin'].iplot(
    title=f'Margin (Overall avg. {in_date_overall_margin}%)', kind='scatter',
          mode='markers', asFigure=True)
fig2['data'].update({'marker': {'size': 6, 'opacity': 0.5}})
fig2['layout'].update({'hovermode': 'closest',
                       'yaxis': {'title': '% Margin', 'range': [0, 100]},
                       'shapes': [{  # add in an overall average line...
                           'type': 'line',  # Overall mean
                           'x0': df_in_date_reshaped['Margin'].index[0],
                           'y0':in_date_overall_margin,
                           'x1':df_in_date_reshaped['Margin'].index[-1],
                           'y1':in_date_overall_margin,
                           'line': {
                               'color': 'rgb(0, 0, 200)',
                               # 'width': 4,
                               # 'dash': 'dash',
                           }
                       }],
                       'annotations': [  # display overall average value
                           dict(x=df_in_date_reshaped['Margin'].index[0],
                                y=in_date_overall_margin,
                                ay=0,
                                ax=-15,
                                showarrow=True,
                                font={'color': 'rgb(0,0,200)'},
                                text=f'{in_date_overall_margin}%')
                       ]
                       })

gr2_margin = dcc.Graph(
    id='gr2',
    figure=fig2,
    style={'height': '80vh'}
)


# 4 Line graph history for individual
df_latest_month = df_in_date[df_in_date.Month == months_dt[-1]]
month_leader = (df_latest_month   # initially show the month leader
                .loc[df_latest_month['Gross sales'].idxmax()]['Consultant'])
fig4 = (df_in_date[df_in_date['Consultant'] == month_leader]
        .set_index('Month_label')
        .iplot(keys=cols_to_graph_4,
               title=f'Consultant History - {month_leader}', asFigure=True))

gr4_bar = dcc.Graph(
    id='gr4',
    figure=fig4,
    style={'height': '87vh'}
)


# Logo
demo_logo = 'DemoLogo.JPG'
encoded_logo = base64.b64encode(open(demo_logo, 'rb').read())


# Dashboard layout
app = dash.Dash()
auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD_PAIRS)

app.layout = html.Div([
    html.H1('Dashboard Demo',
            style={'background': '#0f3d8b', 'color': '#ffffff',
                   'borderRadius': '10', 'paddingLeft': '10',
                   'fontFamily': 'Georgia'}),
    html.H3('Consultant performance over time'),

    html.Div([
        html.Div([
            dcc.RadioItems(
                id='gr1_y_select',
                options=[{'label': i, 'value': i}
                         for i in cols_to_graph_1],
                value=cols_to_graph_1[0],
            )], style={'float': 'left', 'marginTop': '5'}),

        html.Div([
            dcc.Checklist(
                id='gr1_top5',
                options=[{'label': 'Top 5', 'value': 'top5'}],
                values=[],
            )], style={'width': '10%', 'float': 'left',
                       'marginLeft': '15', 'marginTop': '5'}),

        html.Div([
            dcc.Dropdown(
                id='gr6_name_select',
                options=[{'label': i, 'value': i} for i in consultants],
                placeholder='Individual consultant lookup',
            )], style={'width': '15%', 'float': 'left'}),

        html.P('Filter by months: ', id='months_filter',
               style={'float': 'right', 'marginRight': '20%'}),

    ]),
    html.Div([
        dcc.RangeSlider(
            id='month_slider',
            min=0,
            max=num_of_months - 1,
            marks={i: '' for i in range(num_of_months)},
            # Default to the previous 12 months of data
            value=[num_of_months - 12, num_of_months - 1],
        )
    ], style={'width': '80%', 'clear': 'both'}),
    html.Div([
        gr1_line
    ], style={'marginTop': '10', 'width': '60%', 'float': 'left'}),
    html.Div([
        gr2_margin
    ], style={'marginTop': '10', 'width': '40%', 'float': 'right'}),

    html.Hr(),
    html.H3('Monthy breakdown / Consultants ranked'),
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='gr3_month_select',
                options=[{'label': i, 'value': i} for i in months[::-1]],
                value=months[-1],
                clearable=False
            )
        ], style={'width': '200', 'float': 'left'}),
        html.Div([
            dcc.RadioItems(
                id='gr3_y_select',
                options=[{'label': i, 'value': i} for i in cols_to_graph_1],
                value=cols_to_graph_1[0],
                labelStyle={'display': 'inline-block'}
            )], style={'float': 'left', 'marginLeft': '5', 'marginTop': '5'})
    ], ),
    html.Div([
        dcc.Graph(id='gr3', style={'height': '87vh'})
    ], style={'width': '50%', 'marginTop': '10',
              'clear': 'both', 'float': 'left'}),

    html.Div([
        gr4_bar
    ], style={'width': '50%', 'marginTop': '10', 'float': 'right'}),
    html.Hr(style={'clear': 'both'}),
    html.H3(['YTD - Stacked bar graph by Consultant']),
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='gr5_year_select',
                options=[{'label': i, 'value': i} for i in years[::-1]],
                value=years[-1],
                clearable=False
            )],
            style={'width': '200'}),
        html.Div([
            dcc.Graph(id='gr5', style={'height': '88vh'})
        ], style={'width': '100%', 'marginTop': '10'})
    ]),
    html.Hr(),
    html.H3(['Consultant history by Financial Year']),
    html.Div([
        dcc.Dropdown(
            id='gr7_name_select',
            options=[{'label': i, 'value': i} for i in consultants],
            value=month_leader,
            clearable=False
        )], style={'width': '200', 'float': 'left'}),
    html.Div([
            dcc.RadioItems(
                id='gr7_y_select',
                options=[{'label': i, 'value': i}
                         for i in cols_to_graph_7],
                value=cols_to_graph_7[0],
            )], style={'float': 'left', 'marginTop': '5'}),
    html.Div([
        dcc.Graph(id='gr7', style={'height': '88vh'})
    ], style={'clear': 'both', 'width': '100%', 'marginTop': '10'}),
    html.Hr(),
    html.Div([
        html.Img(src='data:image/jpg;base64,{}'.format(encoded_logo.decode()))
    ], style={'textAlign': 'center'})
])

# For investigating and displaying hoverdata
# html.Div([
#     html.Pre(id='hover-data', style={'paddingTop':35})
# ], style={'width':'30%'}),

app.title = 'Dashboard Demo'

# Possible to use CSS for better styling at later date
# app.css.append_css({
#     'external_url': ''
# })


# Callbacks - for selection and hover functionality

# Month selector - title
@app.callback(
    Output('months_filter', 'children'),
    [Input('month_slider', 'value')])
def month_selector_title(months_selected):
    return f'Months selected: {months[months_selected[0]]} \
            - {months[months_selected[1]]}'


# Highlight on hover, gr1
@app.callback(
    Output('gr1', 'figure'),
    [Input('gr1_y_select', 'value'),
     Input('gr1', 'hoverData'),
     Input('gr1_top5', 'values'),
     Input('gr6_name_select', 'value'),
     Input('month_slider', 'value')],
)  # [State('gr1', 'figure')]
def update_graph1(y_select, hoverData, top5, name, months_selected, ):  # fig1
    month_start = months_dt[months_selected[0]]
    month_end = months_dt[months_selected[1]]
    df_in_date = df[(df.Month >= month_start) & (df.Month <= month_end)]
    if name:
        fig6 = (df_in_date[df_in_date['Consultant'] == name]
                .set_index('Month_label')
                .iplot(kind='line', title='Sales/Commission - ' + name,
                       keys=cols_to_graph_6, asFigure=True))
        return fig6
    else:
        df_in_date_reshaped = df_in_date.pivot_table(
            index='Month', columns='Consultant', values=cols_of_interest)
        if top5:
            # find top 5 by total (metric selected) within selected time period
            top5_filter = (df_in_date_reshaped[y_select]
                           .sum().sort_values(ascending=False).head(5).index)
            global top5_selected  # needed to match margin graph on hover
            top5_selected = df_in_date_reshaped[y_select][top5_filter].columns
            fig1 = df_in_date_reshaped[y_select][top5_filter].iplot(
                title=f'{y_select} - Top 5', asFigure=True)
        else:
            fig1 = df_in_date_reshaped[y_select].iplot(
                title=y_select, asFigure=True)
        fig1['layout'].update({'hovermode': 'closest'})

    # Alternate method of controlling x axis
    # Top5 calculations wouldn't be updated
    #
    # 'xaxis':dict(
    #             rangeselector=dict(
    #                 buttons=list([
    #                     dict(count=6,
    #                          label='6m',
    #                          step='month',
    #                          stepmode='backward'),
    #                     dict(count=1,
    #                         label='YTD',
    #                         step='year',
    #                         stepmode='todate'),
    #                     dict(count=1,
    #                         label='1y',
    #                         step='year',
    #                         stepmode='backward'),
    #                     dict(step='all')
    #                 ])
    #             ),
    #             rangeslider=dict() # type='date')

    try:  # Needed try/except to avoid error when no trace hovered over
        hovering_over = hoverData['points'][0]['curveNumber']
        # Highlight trace hovered over
        for n, trace in enumerate(fig1['data']):
            if n == hovering_over:
                # Size of highlighted line
                trace.update(dict(line={'width': 6}))
            else:
                trace.update(dict(line={'width': 1}))
    except Exception as e:
        print(str(e))

    return fig1


# Display Margin history (12months) on gr2
@app.callback(
    Output('gr2', 'figure'),
    [Input('gr1', 'hoverData'),
     Input('gr6_name_select', 'value'),
     Input('gr1_top5', 'values'),
     Input('month_slider', 'value'),
     Input('gr1_y_select', 'value')])
def update_graph2(hoverData, name_input, top5, months_selected, y_select):
    global fig2
    try:
        hovering_over = hoverData['points'][0]['curveNumber']
        if name_input:  # If graphing individual consultant
            name = name_input
            # Since default global 'in date' is 12mo
            df_hov = df_in_date_reshaped['Margin'][name]
        elif top5:  # If graphing top5
            # If top5 selected, names/numbers dont match up, so use global list
            global top5_selected
            name = top5_selected[hovering_over]
            df_hov = df_in_date_reshaped['Margin'][top5_selected].iloc[:, hovering_over]
        else:
            month_start, month_end = months_dt[months_selected[0]], \
                months_dt[months_selected[1]]
            df_in_date = df[(df.Month >= month_start)
                            & (df.Month <= month_end)]
            df_in_date_reshaped_2 = df_in_date.pivot_table(
                index='Month', columns='Consultant', values=cols_of_interest)
            name = df_in_date_reshaped_2[y_select].columns[hovering_over]
            df_hov = df_in_date_reshaped['Margin'][name]
        # mean_margin = round(df_hov.mean())
        # average of margins, can be affected quite a bit by outliers
        # eg. when low amount but high%.
        mean_overall = (round(100 * df_in_date_reshaped['Commission'][name]
                              .sum() / df_in_date_reshaped['Gross sales'][name]
                              .sum()))  # overall using total values
        fig2 = df_hov.iplot(title=f'{name} - Margin history (avg. {mean_overall}%)',
                            asFigure=True, kind='scatter', mode='markers')
        fig2['layout'].update({'hovermode': 'closest',
                               'showlegend': False,
                               'yaxis': {'title': '% Margin',
                                         'range': [0, 100]},
                               'shapes': [
                                   {   # Add line showing Overall average
                                       'type': 'line',
                                       'x0': df_hov.index[0],
                                       'y0':mean_overall,
                                       'x1':df_hov.index[-1],
                                       'y1':mean_overall,
                                       'line': {
                                           'color': 'rgb(0, 0, 200)',
                                                    # 'width': 4,
                                                    'dash': 'dash',
                                       }}
                               ],
                               'annotations': [  # And value of overall average
                                   dict(x=df_hov.index[0],
                                        y=mean_overall,
                                        ay=0,
                                        ax=-15,
                                        showarrow=True,
                                        font={
                                       'color': 'rgb(0,0,200)'},
                                       text=f'{mean_overall}%')
                               ]
                               })
    except Exception as e:
        print(str(e))

    return fig2


# Select month and metric for pie chart gr3
@app.callback(
    Output('gr3', 'figure'),
    [Input('gr3_y_select', 'value'),
     Input('gr3_month_select', 'value')])
def update_graph3(y_select, month):
    pie_df = df_reshaped[y_select].transpose().reset_index()
    pie_df.columns = ['Consultant'] + months

    fig3 = pie_df.iplot(kind='pie', labels='Consultant', values=month,
                        title=f'{y_select} - {month}',
                        textinfo='label+value+percent', asFigure=True)
    return fig3


# Select user for bargraph by hovering on pie chart gr4
@app.callback(
    Output('gr4', 'figure'),
    [Input('gr3', 'hoverData')])
def update_graph4(hoverData):
    global fig4
    try:
        hovering_over = hoverData['points'][0]['label']
        fig4 = (df_in_date[df_in_date['Consultant'] == hovering_over]
                .set_index('Month_label')
                .iplot(keys=cols_to_graph_4,
                       title='Consultant History - ' + hovering_over, asFigure=True))
    except Exception as e:
        print(str(e))

    return fig4


# Select year for ytd bargraph gr5
@app.callback(
    Output('gr5', 'figure'),
    [Input('gr5_year_select', 'value')])
def update_graph5(year_selected):
    global fig5
    if year_selected:
        fig5 = (df[df['Month'].apply(lambda x:x.year) == int(year_selected)]
                .pivot_table(index='Consultant', values=cols_to_graph_5, aggfunc=sum)
                .sort_values(by='Service fee', ascending=False)
                .iplot(kind='bar', barmode='stack',
                       title=f'{year_selected} YTD sales/commission',
                       keys=cols_to_graph_5, asFigure=True)
                )
    return fig5


# Select consultand and metric for gr7
@app.callback(
    Output('gr7', 'figure'),
    [Input('gr7_name_select', 'value'),
     Input('gr7_y_select', 'value')])
def update_graph7(name, metric):
    traces = []
    filter1 = df['Consultant'] == name
    for i, fyr in enumerate(fin_years[:-max_prev_years-1:-1]):  # include up to the last 5 years
        filter2 = df['Financial_year'] == fyr
        trace = go.Scatter(x=df[filter1 & filter2]['Month'].dt.strftime('%b'),
                           y=df[filter1 & filter2][metric],
                           name=fyr,
                           line=dict(
                                color=colour_list[i],
                                width=2+2/(i+1),
                                    )
                           )
        traces.append(trace)
    layout = go.Layout(title=f'{name} - {metric} comparison by Financial Year')
    fig7 = dict(data=traces, layout=layout)
    return fig7

# For testing format of hoverdata
# @app.callback(
#     Output('hover-data', 'children'),
#     [Input('gr1', 'hoverData')])
# def callback_image(hoverData):
#     return json.dumps(hoverData, indent=2)


# Initialise the server
if __name__ == '__main__':
    app.run_server()
