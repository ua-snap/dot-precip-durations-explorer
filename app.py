import os, json, io, requests
import dash 
import dash_table
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
import numpy as np

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #  NSIDC-0051 Derived FUBU Data Explorer Tool                         # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def get_data_return_df( sid ):
    ''' helper function for working with ACIS JSON'''
    sdate = '1979-01-02'
    edate = '2015-10-29'
    elems = 'pcpn'
    output_type = 'json'

    url = 'http://data.rcc-acis.org/StnData?sid={}&sdate={}&edate={}&elems={}&output={}'\
            .format(sid, sdate, edate, elems, output_type )

    # get the station data json
    response = requests.get(url)
    json_data = json.loads(response.text)
    df = pd.DataFrame(json_data['data'], columns=['time','pcpn'])
    df.index = pd.DatetimeIndex(df['time'].values)
    return df['pcpn']

def load_data():
    print('loading remote data files...')
    # load the data
    # wrf
    url = 'https://www.snap.uaf.edu/webshared/Michael/data/pcpt_hourly_communities_v2_ERA-Interim_historical.csv'
    s = requests.get(url).content
    wrf = pd.read_csv(io.StringIO(s.decode('utf-8')), index_col=0, parse_dates=True)
    start, end = wrf.index.min().strftime('%Y-%d-%m'), wrf.index.max().strftime('%Y-%d-%m')
    # harvest acis
    sids = {'Barrow':'USW00027502', 'Nome':'USW00026617', 'Bethel':'USW00026615', \
    'Anchorage':'USW00026451', 'Juneau':'USW00025309', 'Fairbanks':'USW00026411',} #'Homer':'USC00503672
    df = pd.DataFrame({ name:get_data_return_df( sid ) for name,sid in sids.items() })
    df = df.replace('M', np.nan).replace('T', '.001').astype(np.float32)
    acis = df*25.4 # make mm
    print('data loaded.')
    return wrf, acis

# def load_data():
#     print('loading local data files...')
#     base_dir = '/Users/malindgren/Documents/repos/dot-precip-explorer/data'
#     wrf = pd.read_csv(os.path.join(base_dir,'wrf-data.csv'), index_col=0, parse_dates=True )
#     acis = pd.read_csv(os.path.join(base_dir,'acis-data.csv'), index_col=0, parse_dates=True )
#     print('data loaded.')
#     return wrf, acis

# load data
wrf, acis = load_data()

# get the range of years
years = acis.index.map(lambda x: x.year).unique()

app = dash.Dash(__name__)
server = app.server
server.secret_key = os.environ['SECRET-SNAP-KEY']
# server.secret_key = 'secret_key'
app.config.supress_callback_exceptions = True
app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})
app.title = 'WRF-ACIS-Precip-Compare'

# durations we are examining
durations_lu = {'60-min':'1H','2-hr':'2H','3-hr':'3H','6-hr':'6H','12-hr':'12H','24-hr':'1D','2-day':'2D','3-day':'3D','4-day':'4D','7-day':'7D','10-day':'10D','20-day':'20D','30-day':'30D','45-day':'45D','60-day':'60D'}
durations_lu_flip = {durations_lu[i]:i for i in durations_lu}

# PAGE LAYOUT
app.layout = html.Div([
                html.Div([
                    html.H3('Compare Annual Precip at Select Locations and Durations', style={'font-weight':'bold'}),
                    ]),

                html.Div([ 
                    html.Div([
                        html.Div([ # group1
                            html.Div([
                                html.Label('Choose Community', style={'font-weight':'bold'})
                                ], className='three columns'),
                            html.Div([
                                dcc.Dropdown(
                                        id='community-dd',
                                        options=[{'label':i,'value':i} for i in wrf.columns],
                                        value='Fairbanks',
                                        clearable=False)
                                    ], className='three columns'),
                            ], className='row'),
                        html.Div([ # group2
                            html.Div([
                                html.Label('Choose Duration', style={'font-weight':'bold'})
                                ], className='three columns'),
                            html.Div([
                                dcc.Dropdown(
                                    id='duration-dd',
                                    options=[{'label':key,'value':durations_lu[key]} for key in durations_lu],
                                    value='1D' ,
                                    clearable=False),
                                ], className='three columns'),
                            ], className='row'),
                        html.Div([
                            html.Div([
                                html.Label('Choose Metric', style={'font-weight':'bold'})
                                ], className='three columns'),
                            html.Div([
                                dcc.Dropdown(
                                    id='metric-dd',
                                    options=[{'label':i,'value':i} for i in ['mean','max']], #'min' is not useful since the min will pretty much always be 0mm
                                    value='max',
                                    clearable=False),
                                ], className='three columns'),
                            ], className='row'),
                        ], className='six columns'),
                    html.Div([
                        dcc.Markdown(id='corr-label')
                        ], className='three columns'),
                    ], className='row' ),

                html.Div([
                    html.Div([dcc.Graph( id='acis-wrf-graph' )]),
                    # html.Div([
                    #     dcc.RangeSlider(
                    #         id='time-slider',
                    #         marks={i:str(i) for i in years},
                    #         min=min(years),
                    #         max=max(years),
                    #         value=[min(years), max(years)],
                    #         pushable=True)
                    #     ]),
                    ], className='eleven columns'),
                html.Div([
                    dash_table.DataTable(
                        id='data-table',
                        columns=[{"name":'', "id":''}]+[{"name": i, "id": i} for i in years],
                        # data=df.to_dict("rows"),
                        )
                    ], className='twelve columns'),
                    html.Div([html.Label(' ')]),
                ])


@app.callback(Output('thresh-value', 'children'),
            [Input('my-slider', 'value')])
def update_thresh_value( thresh ):
    return 'threshold: {}'.format(thresh)

@app.callback([Output('acis-wrf-graph', 'figure'),
            Output('corr-label','children'),
            Output('data-table','data'),],
            # [Input('time-slider', 'value'),
            [Input('community-dd', 'value'),
            Input('duration-dd', 'value'),
            Input('metric-dd','value'),])
def update_graph(  community, duration, metric ): # time_range,
    # time
    # begin,end = time_range
    # begin = str(begin)
    # end = str(end)
    
    # pull data for the year we want to examine
    wrf_sub = wrf[community].copy(deep=True).astype(np.float32)
    acis_sub = acis[community].copy(deep=True).astype(np.float32)
    
    metric_lu = {'min':'Min', 'mean':'Mean', 'max':'Max'}
    # duration and plot title-fu
    title = 'ERA-Interim / ACIS Daily Precip Total' # base title if None
    # if (duration is not None) and (community is not None) and (metric is not None):
    print(duration)
    title = 'ERA-Interim / ACIS {} Precip Total - Annual {}'.format( durations_lu_flip[duration], community, metric_lu[metric] )

    # make duration
    wrf_res = wrf_sub.resample(duration).sum()
    acis_res = acis_sub.resample(duration).sum()

    # if duration > 0:
    #     if duration == 366:
    #         wrf_res = wrf_sub.resample('Y')#.max()
    #         acis_res = acis_sub.resample('Y')#.max()
    #         title = 'ERA-Interim / ACIS Daily Precip Total: {} - {} {}'.format(community, 'Annual', metric_lu[metric])
    #     elif duration == 555:
    #         wrf_res = wrf_sub.resample('M')#.max()
    #         acis_res = acis_sub.resample('M')#.max()
    #         title = 'ERA-Interim / ACIS Daily Precip Total: {} - {} {}'.format(community, 'Monthly', metric_lu[metric])
    #     else:
    #         wrf_res = wrf_sub.resample('{}D'.format(duration))#.mean()
    #         acis_res = acis_sub.resample('{}D'.format(duration))#.mean()
    #         title = 'ERA-Interim / ACIS Daily Precip Total: {} - {} Day {}'.format(community, duration, metric_lu[metric])

    # make annuals
    wrf_ann = wrf_res.resample('Y')
    acis_ann = acis_res.resample('Y')

    # handle metric choice... -- UGGGO
    if metric == 'min':
        wrf_ann = wrf_ann.min().copy()
        acis_ann = acis_ann.min().copy()
    elif metric == 'mean':
        wrf_ann = wrf_ann.mean().copy()
        acis_ann = acis_ann.mean().copy()
    else: # always use max
        wrf_ann = wrf_ann.max().copy()
        acis_ann = acis_ann.max().copy()

    # get some correlation coefficients
    pearson = wrf_ann.corr( acis_ann, method='pearson' ).round(2)
    spearman = wrf_ann.corr( acis_ann, method='spearman' ).round(2)
    kendall = wrf_ann.corr( acis_ann, method='kendall' ).round(2)

    # slice to the year-range selected
    wrf_ann = wrf_ann.round(2)
    acis_ann = acis_ann.round(2)

    df = pd.concat([wrf_ann, acis_ann], axis=1)
    df.columns = ['wrf','acis']
    df.index = df.index.map(lambda x: x.year)
    df = df.applymap("{0:.1f}".format).T.reset_index()
    df.columns = [ i if i != 'index' else '' for i in df.columns ]

    # build Graph object
    graph = {'data':[ 
                go.Bar(
                    x=wrf_ann.index,
                    y=wrf_ann,
                    name='wrf',
                    ),
                go.Bar(
                    x=acis_ann.index,
                    y=acis_ann,
                    name='acis',
                    ),
                ],
            'layout': { 
                    'title': title,
                    'xaxis': dict(title='time'),
                    'yaxis': dict(title='mm'),
                    # 'uirevision': time_range, # [watch]hold State of Graph
                    }
            }
    # output correlation values
    corr_value = '''
        WRF/ACIS Series Correlation:
          pearson : {}
          spearman: {}
          kendall : {}
    '''.format(pearson,spearman,kendall)
    return graph, corr_value, df.to_dict('rows')

if __name__ == '__main__':
    app.run_server( debug=False )
