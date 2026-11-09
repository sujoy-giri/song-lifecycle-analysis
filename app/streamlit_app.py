from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed'
TABLES = ROOT / 'outputs' / 'tables'
STAGES = ['New Entry', 'Growth', 'Peak', 'Mature', 'Decline', 'Fringe']
STAGE_COLORS = {'New Entry': '#4C78A8', 'Growth': '#54A24B', 'Peak': '#F58518',
                'Mature': '#B279A2', 'Decline': '#E45756', 'Fringe': '#9D9D9D'}

st.set_page_config(page_title='Songs Streaming Lifecycle Analytics', layout='wide')


@st.cache_data
def load_data():
    days = pd.read_csv(DATA / 'spain_top50_staged.csv', parse_dates=['date'])
    songs = pd.read_csv(
        DATA / 'lifecycle_enriched.csv',
        parse_dates=['entry_date', 'exit_date', 'peak_date', 'first_run_peak_date'],
    )
    daily = pd.read_csv(TABLES / 'daily_churn.csv', parse_dates=['date'])
    return days, songs, daily


days, songs, daily = load_data()

# ---------- Sidebar filters ----------
st.sidebar.header('Filters')
first_day, last_day = days['date'].min().date(), days['date'].max().date()
picked = st.sidebar.date_input('Date range', (first_day, last_day),
                               min_value=first_day, max_value=last_day)
if len(picked) != 2:          # the widget returns one date while the user is mid-selection
    st.info('Pick an end date to continue.')
    st.stop()
start, end = picked

content = st.sidebar.radio('Content', ['All', 'Explicit only', 'Clean only'])
formats = st.sidebar.multiselect('Release format', ['single', 'album'], default=['single', 'album'])
stages = st.sidebar.multiselect('Lifecycle stage', STAGES, default=STAGES)

# ---------- Apply filters ----------
base_mask = (
    (days['date'].dt.date >= start) & (days['date'].dt.date <= end)
    & days['album_type'].isin(formats)
)
if content == 'Explicit only':
    base_mask &= days['is_explicit']
elif content == 'Clean only':
    base_mask &= ~days['is_explicit']
base = days[base_mask]                       # all stages, for tabs where the stage filter shouldn't apply
view = base[base['stage'].isin(stages)]      # what the other tabs use

if view.empty:
    st.warning('No chart days match these filters.')
    st.stop()

# ---------- Header and headline numbers ----------
st.title('Songs Streaming Lifecycle Analytics')
st.caption('Spain Top 50, daily chart data prepared for Atlantic Recording Corporation')

c1, c2, c3 = st.columns(3)
c1.metric('Songs', f"{view.groupby(['song_key', 'artist_key']).ngroups:,}")
c2.metric('Song-days', f"{len(view):,}")
c3.metric('Days covered', f"{view['date'].nunique():,}")
st.caption('The data has 555 of 559 calendar days; four dates are missing from the source and were not filled.')

with st.expander('About this dashboard'):
    st.markdown(
        '**Data:** daily Spain Top 50 chart, 18 May 2024 to 27 Nov 2025 (555 of 559 calendar days; '
        'the four missing dates were not filled).\n\n'
        '**Preparation:** one date had two conflicting snapshots and the first was kept. Song and artist names '
        'were matched ignoring capitalization. Song details that changed over time use the most recent value. '
        'Popularity values of 0, mostly a first-day placeholder, are treated as missing.\n\n'
        '**Reading it:** a run is an unbroken streak of chart days, and a returning song starts a new run. '
        'Fringe runs are 5 days or fewer that never reach the top 40. Exits are not charted separately: the chart '
        'always holds 50 songs, so the number leaving each day equals the number entering.\n\n'
        '**Caution:** differences between groups, such as explicit vs clean or single vs album, are associations '
        'in this data and not proof of cause.'
    )

tab_song, tab_stages, tab_churn, tab_content = st.tabs(['Song explorer', 'Stages', 'Churn', 'Content'])

with tab_song:
    st.subheader('Song explorer')
    st.caption('The song list follows your filters. The chart shows the song’s full history and ignores them.')

    options = (
        view.groupby(['song_key', 'artist_key'])
        .agg(song=('song', 'first'), artist=('artist', 'first'), chart_days=('date', 'size'))
        .reset_index()
        .sort_values('chart_days', ascending=False)
    )
    options['label'] = options['song'] + ' - ' + options['artist']
    label = st.selectbox('Song (type to search)', options['label'].tolist())
    pick = options[options['label'] == label].iloc[0]

    same_song = (days['song_key'] == pick['song_key']) & (days['artist_key'] == pick['artist_key'])
    history = days[same_song].sort_values('date')
    info = songs[(songs['song_key'] == pick['song_key']) & (songs['artist_key'] == pick['artist_key'])].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Days on chart', int(info['days_on_chart']))
    m2.metric('Best position', int(info['peak_position']))
    m3.metric('Separate runs', int(info['num_runs']))
    m4.metric('First seen', info['entry_date'].strftime('%d %b %Y'))
    if info['entered_before_data'] or info['still_on_chart']:
        st.caption('This song was already charting when the data begins, or still charting when it ends, '
                   'so its totals are partial.')

    fig = go.Figure()
    for _, run in history.groupby('run_id'):
        fig.add_trace(go.Scatter(x=run['date'], y=run['position'], mode='lines',
                                 line=dict(color='lightgray', width=1),
                                 showlegend=False, hoverinfo='skip'))
    for stage in STAGES:
        part = history[history['stage'] == stage]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(x=part['date'], y=part['position'], mode='markers', name=stage,
                                 marker=dict(color=STAGE_COLORS[stage], size=8),
                                 hovertemplate='%{x|%d %b %Y}<br>Position %{y}<extra>' + stage + '</extra>'))
    fig.update_yaxes(range=[50.5, 0.5], title='Chart position (1 = top)')
    fig.update_layout(title='Chart position by day, colored by lifecycle stage')
    st.plotly_chart(fig)

    pop_fig = go.Figure()
    for _, run in history.groupby('run_id'):
        run = run[run['popularity'] > 0]   # zeros are placeholders, treated as missing
        pop_fig.add_trace(go.Scatter(x=run['date'], y=run['popularity'], mode='lines+markers',
                                     line=dict(color='#4C78A8'), showlegend=False))
    pop_fig.update_layout(title='Spotify popularity (lines break where the song left the chart)',
                          yaxis_title='Popularity')
    st.plotly_chart(pop_fig)


with tab_stages:
    st.subheader('Stage distribution')
    st.caption('Share of chart days spent in each lifecycle stage. '
               'This tab ignores the stage filter, since filtering stages would change the shares.')

    counts = base['stage'].value_counts().reindex(STAGES).fillna(0)
    share = (counts / counts.sum() * 100).round(1)

    fig_stage = px.bar(x=STAGES, y=share.values, color=STAGES, color_discrete_map=STAGE_COLORS,
                       text=share.values, labels={'x': 'Stage', 'y': '% of chart days'})
    fig_stage.update_traces(texttemplate='%{text}%')
    fig_stage.update_traces(textposition='outside')
    fig_stage.update_layout(showlegend=False)
    st.plotly_chart(fig_stage)

    st.caption('In the full data, fringe runs are only about 2% of chart days but about 31% of all chart runs.')

    with st.expander('How the stages are defined'):
        st.markdown(
            '- **New Entry:** the first 3 days of a chart run\n'
            '- **Peak:** within 3 positions of the run’s best position\n'
            '- **Growth:** days before the run first reaches that peak zone\n'
            '- **Decline:** more than 10 positions worse than the run’s best, and still sliding versus a week earlier\n'
            '- **Mature:** after the peak, not in decline\n'
            '- **Fringe:** runs of 5 days or fewer that never reach the top 40, so no lifecycle stage applies\n\n'
            'A run is an unbroken streak of chart days. A song that leaves the chart and returns starts a new run.'
        )


with tab_churn:
    st.subheader('Churn and rotation')
    st.caption('An entry is the first day of a chart run, so returning songs count. This tab follows the date, '
               'content and format filters and ignores the stage filter. Counts cover the selected songs only, '
               'so "share of the chart replaced" applies only when all songs are selected.')

    # Days to leave out: the first data date and the day after each missing date (as in Notebook 04)
    skip_dates = pd.DatetimeIndex(daily.loc[daily['after_gap'], 'date']).append(
        pd.DatetimeIndex([days['date'].min()]))
    all_dates = pd.DatetimeIndex(days['date'].unique()).sort_values().difference(skip_dates)
    all_dates = all_dates[(all_dates >= pd.Timestamp(start)) & (all_dates <= pd.Timestamp(end))]

    if len(all_dates) == 0:
        st.warning('No measurable days in this date range.')
    else:
        entries = base[(base['day_in_run'] == 1) & base['date'].isin(all_dates)]
        per_day = entries.groupby('date').size().reindex(all_dates, fill_value=0)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Mean entries per day', f'{per_day.mean():.2f}')
        m2.metric('Median entries per day', f'{per_day.median():g}')
        m3.metric('Fringe share of entries', f"{entries['is_fringe'].mean():.0%}" if len(entries) else 'n/a')
        m4.metric('Re-entry share of entries', f"{(entries['run_id'] > 1).mean():.0%}" if len(entries) else 'n/a')

        rolling = per_day.rolling(7, min_periods=4).mean()
        fig_d = go.Figure()
        fig_d.add_trace(go.Bar(x=per_day.index, y=per_day.values, name='Daily entries', marker_color='lightgray'))
        fig_d.add_trace(go.Scatter(x=rolling.index, y=rolling.values, name='7-day average',
                                   line=dict(color='#4C78A8', width=2)))
        fig_d.update_layout(title='Songs entering the chart per day', yaxis_title='Entries')
        st.plotly_chart(fig_d)

        monthly = per_day.groupby(per_day.index.to_period('M')).agg(['mean', 'median'])
        monthly.index = monthly.index.to_timestamp()
        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(x=monthly.index, y=monthly['mean'], mode='lines+markers', name='Mean',
                                   line=dict(color='#4C78A8')))
        fig_m.add_trace(go.Scatter(x=monthly.index, y=monthly['median'], mode='lines+markers', name='Median',
                                   line=dict(color='#F58518')))
        fig_m.update_layout(title='Monthly entries per day', yaxis_title='Entries per day')
        st.plotly_chart(fig_m)
        st.caption('May 2024 and November 2025 are partial months. The mean sits above the median because of '
                   'occasional release-day reshuffles of 13 to 23 entries.')



with tab_content:
    st.subheader('Content attributes and chart longevity')
    st.caption('This tab compares fixed groups of songs, so it ignores the sidebar filters. '
               'Longevity is the number of days a song spent on the chart in the 90 days after it entered. '
               'Songs that began before the data starts, or entered less than 90 days before it ends, '
               'are left out of that column because their 90-day window is incomplete.')

    def compare_groups(col, names=None):
        t = songs.groupby(col).agg(
            songs=('song_key', 'size'),
            with_90_day_window=('days_90', 'count'),
            median_days_first_90=('days_90', 'median'),
            median_best_position=('peak_position', 'median'),
            top10_share=('top10', 'mean'),
        )
        if names:
            t = t.rename(index=names)
        t['top10_share'] = t['top10_share'].map('{:.0%}'.format)
        t.index.name = None
        t = t.rename(columns={'songs': 'Songs', 'with_90_day_window': 'Songs with full 90-day window',
                              'median_days_first_90': 'Median days on chart (first 90)',
                              'median_best_position': 'Median best position', 'top10_share': 'Reached top 10'})
        return t

    st.markdown('**Explicit vs clean**')
    st.dataframe(compare_groups('is_explicit', {False: 'Clean', True: 'Explicit'}))
    st.markdown('**Single vs album**')
    st.dataframe(compare_groups('album_type'))
    st.caption('In the analysis, singles stayed a median of 16 days longer than album tracks in their first 90 days '
               '(95% interval 5 to 27 days). Explicit and clean songs showed no detectable difference '
               '(0 days, interval -8.5 to 7). These are comparisons between groups, not proof of cause: '
               'artist and genre were not examined.')

    st.markdown('---')
    st.subheader('Why the single vs album gap appears: how many songs debut together')

    new = songs[~songs['entered_before_data']].merge(
        daily.loc[~daily['after_gap'], ['date', 'new_songs']]
             .rename(columns={'date': 'entry_date', 'new_songs': 'cohort_size'}),
        on='entry_date', how='inner')
    new['cohort'] = pd.cut(new['cohort_size'], bins=[0, 1, 3, 7, 100],
                           labels=['1 new song', '2-3', '4-7', '8+'])

    by_group = (new.groupby(['cohort', 'album_type'], observed=True)['days_90']
                .agg(songs='count', median_days='median').reset_index())
    plot_data = by_group[by_group['songs'] >= 30]

    fig_c = px.line(plot_data, x='cohort', y='median_days', color='album_type', markers=True,
                    color_discrete_map={'album': '#4C78A8', 'single': '#F58518'},
                    category_orders={'cohort': ['1 new song', '2-3', '4-7', '8+']},
                    labels={'cohort': 'New songs debuting on the same day',
                            'median_days': 'Median days on chart (first 90)',
                            'album_type': 'Release format'})
    st.plotly_chart(fig_c)
    st.dataframe(by_group.pivot(index='cohort', columns='album_type', values=['songs', 'median_days']))
    st.caption('Chart stays shrink as more songs debut on the same day. 47% of album tracks with a full 90-day '
               'window debuted in a group of eight or more new songs, against 4% of singles. Points based on '
               'fewer than 30 songs are not drawn, though the table still lists them. The table leaves out '
               '4 singles that debuted the day after a missing date, so single counts add to 194 and not 198.')