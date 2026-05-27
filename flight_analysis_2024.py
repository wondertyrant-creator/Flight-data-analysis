**SECTION 1: IMPORTS AND DATA LOADING**
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')

df = pd.read_csv('/content/flight_data_2024.csv', dtype={'cancellation_code': str}, low_memory=False)
df['fl_date'] = pd.to_datetime(df['fl_date'], dayfirst=True, format='mixed')

"""**SECTION 2: INITIAL DATA EXPLORATION**"""

df.info()

df.shape

df.head()

print(df['op_unique_carrier'].value_counts())

unique_flights_count = df.groupby(['op_unique_carrier', 'op_carrier_fl_num']).ngroups
print(f"\nNumber of unique flight numbers: {unique_flights_count}")

print("\n--- Unique Origin Airports per Carrier ---")
unique_origins_per_carrier = (
    df.groupby('op_unique_carrier')['origin']
    .nunique()
    .sort_values(ascending=False)
    .rename('unique_origins')
)
display(unique_origins_per_carrier)

print("\n--- Unique Origin Airports per Carrier ---")
unique_origins_per_carrier = (
    df.groupby('op_unique_carrier')['origin']
    .nunique()
    .sort_values(ascending=False)
    .rename('unique_origins')
)
display(unique_origins_per_carrier)

"""**SECTION 3: DATA QUALITY**"""

df.duplicated().sum()

df.isnull().sum()

"""Null handling for delay columns"""

DELAY_COLS = ['carrier_delay', 'weather_delay', 'nas_delay',
              'security_delay', 'late_aircraft_delay']
df[DELAY_COLS] = df[DELAY_COLS].fillna(0)

"""Outlier detection"""

p99_dep = df['dep_delay'].quantile(0.99)
p99_arr = df['arr_delay'].quantile(0.99)
df['is_outlier'] = (df['dep_delay'] > p99_dep) | (df['arr_delay'] > p99_arr)

outlier_count = df['is_outlier'].sum()
outlier_pct   = outlier_count / len(df) * 100
print(f"\nOutlier threshold  — dep_delay > {p99_dep:.0f} min  OR  arr_delay > {p99_arr:.0f} min")
print(f"Outlier flights    — {outlier_count:,} ({outlier_pct:.2f}% of dataset)")

print("\nImpact of outliers on avg departure delay per carrier:")
impact = pd.DataFrame({
    'with_outliers':    df.groupby('op_unique_carrier')['dep_delay'].mean().round(2),
    'without_outliers': df[~df['is_outlier']].groupby('op_unique_carrier')['dep_delay'].mean().round(2),
})
impact['difference'] = (impact['with_outliers'] - impact['without_outliers']).round(2)
display(impact.sort_values('difference', ascending=False))

"""**SECTION 4: FEATURE ENGINEERING**"""

df['total_delay']      = df['dep_delay'] + df['arr_delay']
df['is_on_time']       = df['arr_delay'] <= 15
df['is_severely_late'] = df['dep_delay'] > 60

delay_mag_bins   = [-float('inf'), 0, 15, 60, 120, float('inf')]
delay_mag_labels = ['Early / On Time', 'Minor (1–15 min)',
                    'Moderate (16–60 min)', 'Severe (61–120 min)', 'Extreme (>120 min)']
df['delay_magnitude'] = pd.cut(df['dep_delay'], bins=delay_mag_bins, labels=delay_mag_labels)

"""Time features"""

df['season'] = pd.cut(df['month'],
    bins=[0, 2, 5, 8, 11, 12],
    labels=['Winter', 'Spring', 'Summer', 'Autumn', 'Winter'],
    ordered=False
)

df['season'] = df['season'].astype(str)

df['scheduled_departure_hour'] = df['crs_dep_time'] // 100
df['is_weekend'] = df['day_of_week'].isin([6, 7])

df['day_type'] = df['is_weekend'].map({True: 'Weekend', False: 'Weekday'})

"""Aircraft performance"""

df['schedule_padding'] = df['crs_elapsed_time'] - df['actual_elapsed_time']
df['ground_speed'] = df['distance'] / df['air_time']

padding_bins   = [-float('inf'), -10, 0, 10, 20, float('inf')]
padding_labels = ['Severely Under-padded (<-10 min)', 'Slightly Under-padded (-10–0 min)',
                  'Tight Padding (0–10 min)', 'Moderate Padding (10–20 min)', 'Heavy Padding (>20 min)']
df['padding_category'] = pd.cut(df['schedule_padding'], bins=padding_bins, labels=padding_labels)

"""Flight classification"""

df['flight_type'] = np.where(df['distance'] > 1800, 'Long-haul', 'Short-haul')

"""Distance bands (used in route analysis)"""

dist_bins = [0, 500, 1000, 1500, 2000, 3000, float('inf')]
dist_labels = ['<500mi', '500–1000mi', '1000–1500mi', '1500–2000mi', '2000–3000mi', '>3000mi']

df['distance_band'] = pd.cut(df['distance'], bins=dist_bins, labels=dist_labels)

df.head()

"""**SECTION 5: AIRPORT ANALYSIS**

Busiest airports by departure volume
"""

busiest_airports = df['origin'].value_counts().head(10)
display(busiest_airports)

"""Longest average taxi-out times"""

longest_taxi_out = (
    df.groupby('origin')['taxi_out']
    .mean()
    .sort_values(ascending=False)
    .round(2)
    .head(20)
)
display(longest_taxi_out)

"""Airport congestion score"""

congestion_score = (
    df.groupby('origin')
    .agg(
        avg_taxi_out=('taxi_out', 'mean'),
        avg_nas_delay=('nas_delay', 'mean'),
        flight_volume=('op_carrier_fl_num', 'count')
    )
    .query('flight_volume >= 100')
    .assign(congestion_score=lambda x: (x['avg_taxi_out'] + x['avg_nas_delay']).round(2))
    .sort_values('congestion_score', ascending=False)
    .round(2)
)

print("Most Congested:")
display(congestion_score.head(20))
print("Least Congested:")
display(congestion_score.tail(20))

"""Congestion by hour of day"""

congestion_by_hour = (
    df.groupby('scheduled_departure_hour')
    .agg(
        avg_taxi_out=('taxi_out', 'mean'),
        avg_nas_delay=('nas_delay', 'mean')
    )
    .assign(congestion_score=lambda x: (x['avg_taxi_out'] + x['avg_nas_delay']).round(2))
    .round(2)
)
display(congestion_by_hour)

"""Late aircraft ripple effect by origin"""

late_aircraft_by_origin = (
    df.groupby('origin')['late_aircraft_delay']
    .mean()
    .sort_values(ascending=False)
    .round(2)
    .head(20)
)
display(late_aircraft_by_origin)

"""**SECTION 6: CARRIER ANALYSIS**

Delay magnitude distribution per carrier
"""

delay_mag_by_carrier = (
    df.groupby(['op_unique_carrier', 'delay_magnitude'], observed=True)
    .size()
    .groupby(level=0)
    .transform(lambda x: x / x.sum() * 100)
    .unstack()
    .round(2)
)
display(delay_mag_by_carrier)

"""Mean vs median delay and % severely late (>60 min) by carrier"""

delay_summary_by_carrier = (
    df.groupby('op_unique_carrier')
    .agg(
        mean_dep_delay=('dep_delay', 'mean'),
        median_dep_delay=('dep_delay', 'median'),
        pct_severely_late=('is_severely_late', lambda x: round(x.mean() * 100, 2))
    )
    .round(2)
    .sort_values('mean_dep_delay', ascending=False)
)
display(delay_summary_by_carrier)

"""On-time performance % by carrier"""

otp_by_carrier = (
    df.groupby('op_unique_carrier')['is_on_time']
    .mean()
    .mul(100)
    .round(2)
    .sort_values(ascending=False)
    .rename('on_time_pct')
)
display(otp_by_carrier)

"""Cancellation rate by carrier"""

if 'cancelled' in df.columns:
    cancellation_by_carrier = (
        df.groupby('op_unique_carrier')
        .agg(
            total_flights=('cancelled', 'count'),
            cancellations=('cancelled', 'sum'),
            cancellation_rate_pct=('cancelled', lambda x: round(x.mean() * 100, 2))
        )
        .sort_values('cancellation_rate_pct', ascending=False)
    )
    display(cancellation_by_carrier)

    if 'cancellation_code' in df.columns:
        cancel_reason_map = {'A': 'Carrier', 'B': 'Weather', 'C': 'NAS', 'D': 'Security'}
        cancelled_flights = df[df['cancelled'] == 1].copy()
        cancelled_flights['cancel_reason'] = cancelled_flights['cancellation_code'].map(cancel_reason_map)

        print("\nCancellation Reasons by Carrier (% of that carrier's cancellations):")
        cancel_reasons = (
            cancelled_flights.groupby(['op_unique_carrier', 'cancel_reason'])
            .size()
            .groupby(level=0)
            .transform(lambda x: x / x.sum() * 100)
            .unstack()
            .fillna(0)
            .round(2)
        )
        display(cancel_reasons)

        print("\nOverall Cancellation Reason Breakdown:")
        overall_cancel = (
            cancelled_flights['cancel_reason']
            .value_counts(normalize=True)
            .mul(100)
            .round(2)
        )
        display(overall_cancel)
else:
    print("  'cancelled' column not found — skipping cancellation analysis.")

"""Schedule padding by carrier"""

padding_by_carrier = (
    df.groupby('op_unique_carrier')['schedule_padding']
    .agg(['mean', 'median', 'std'])
    .round(2)
    .rename(columns={'mean': 'avg_padding', 'median': 'median_padding', 'std': 'padding_std'})
    .sort_values('avg_padding', ascending=False)
)
display(padding_by_carrier)

"""Schedule padding effectiveness"""

padding_vs_otp = (
    df.groupby('padding_category', observed=True)
    .agg(
        flight_count=('is_on_time', 'count'),
        on_time_pct=('is_on_time', lambda x: round(x.mean() * 100, 2)),
        avg_arr_delay=('arr_delay', lambda x: round(x.mean(), 2))
    )
)
display(padding_vs_otp)

padding_corr = df[['schedule_padding', 'arr_delay']].corr().round(3)
print(f"\nCorrelation — schedule padding vs arrival delay:\n{padding_corr}")

"""Catch-up factor"""

late_departures    = df[df['dep_delay'] > 0]
on_time_after_late = late_departures[late_departures['arr_delay'] <= 0]
catch_up_factor = (
    on_time_after_late.groupby('op_unique_carrier').size()
    / late_departures.groupby('op_unique_carrier').size()
).round(3).sort_values(ascending=False)
display(catch_up_factor)

"""Ground speed vs flight mix"""

merged_carrier_data = (
    df.groupby('op_unique_carrier')['ground_speed'].mean()
    .to_frame()
    .join(
        df.groupby('op_unique_carrier')['flight_type']
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
    )
    .sort_values('ground_speed', ascending=False)
    .round(3)
)
display(merged_carrier_data)

"""Weekend Penalty by Carrier"""

print("\nWeekend Penalty by Carrier (Weekend − Weekday avg dep_delay):")
print("Positive = worse on weekends | Negative = better on weekends")
weekend_by_carrier = (
    df.groupby(['op_unique_carrier', 'day_type'])['dep_delay']
    .mean()
    .round(2)
    .unstack()
    .assign(weekend_penalty=lambda x: (x['Weekend'] - x['Weekday']).round(2))
    .sort_values('weekend_penalty', ascending=False)
)
display(weekend_by_carrier)

"""Late aircraft ripple effect by carrier"""

ripple_by_carrier = (
    df.groupby('op_unique_carrier')[['late_aircraft_delay', 'carrier_delay']]
    .mean()
    .round(2)
    .sort_values('late_aircraft_delay', ascending=False)
)
display(ripple_by_carrier)

"""**SECTION 7: DELAY CAUSE ANALYSIS**

Frequency: how many flights were affected by each cause
"""

delay_cause_counts = (df[DELAY_COLS] > 0).sum().sort_values(ascending=False)
display(delay_cause_counts)

"""Average minutes contributed per cause across all flights"""

avg_delay_by_cause = df[DELAY_COLS].mean().sort_values(ascending=False).round(2)
display(avg_delay_by_cause)

"""Cause breakdown by season"""

delay_reason_by_season = df.groupby('season')[DELAY_COLS].mean().round(2)
display(delay_reason_by_season)

"""Late aircraft ripple effect by hour"""

late_aircraft_by_hour = (
    df.groupby('scheduled_departure_hour')['late_aircraft_delay']
    .mean()
    .round(2)
)
display(late_aircraft_by_hour)

"""On-time performance and avg delay by hour of day"""

avg_delay_by_hour = df.groupby('scheduled_departure_hour')['dep_delay'].mean().round(2)
otp_by_hour = (
    df.groupby('scheduled_departure_hour')['is_on_time']
    .mean().mul(100).round(2).rename('on_time_pct')
)
hour_summary = pd.concat([avg_delay_by_hour.rename('avg_dep_delay'), otp_by_hour], axis=1)
display(hour_summary)

"""**SECTION 8: TEMPORAL PATTERNS**"""

day_names = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
             4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}

"""Full day-of-week breakdown"""

delay_by_day = (
    df.groupby('day_of_week')
    .agg(
        avg_dep_delay=('dep_delay', 'mean'),
        avg_arr_delay=('arr_delay', 'mean'),
        on_time_pct=('is_on_time', lambda x: round(x.mean() * 100, 2)),
        flight_count=('dep_delay', 'count')
    )
    .round(2)
)
delay_by_day.index = delay_by_day.index.map(day_names)
display(delay_by_day)

"""Weekend vs weekday with full cause breakdown"""

weekend_vs_weekday = (
    df.groupby('day_type')
    .agg(
        avg_dep_delay=('dep_delay', 'mean'),
        avg_arr_delay=('arr_delay', 'mean'),
        on_time_pct=('is_on_time', lambda x: round(x.mean() * 100, 2)),
        avg_weather_delay=('weather_delay', 'mean'),
        avg_carrier_delay=('carrier_delay', 'mean'),
        avg_late_aircraft_delay=('late_aircraft_delay', 'mean'),
        avg_nas_delay=('nas_delay', 'mean'),
        flight_count=('dep_delay', 'count')
    )
    .round(2)
)
display(weekend_vs_weekday)

"""Monthly trends"""

avg_delay_by_month = df.groupby('month')['dep_delay'].mean().round(2)
display(avg_delay_by_month)

"""Seasonal trends"""

avg_delay_by_season = (
    df.groupby('season')['dep_delay']
    .mean().round(2)
    .sort_values(ascending=False)
)
display(avg_delay_by_season)

"""**SECTION 9: ROUTE ANALYSIS**

On-time performance by route
"""

otp_by_route = (
    df.groupby(['origin', 'dest'])
    .agg(
        total_flights=('is_on_time', 'count'),
        on_time_pct=('is_on_time', lambda x: round(x.mean() * 100, 2)),
        avg_arr_delay=('arr_delay', lambda x: round(x.mean(), 2))
    )
    .query('total_flights >= 50')
)
print("Worst 20 Routes for On-Time Arrival:")
display(otp_by_route.sort_values('on_time_pct').head(20))
print("Best 20 Routes for On-Time Arrival:")
display(otp_by_route.sort_values('on_time_pct', ascending=False).head(20))

"""Distance vs delay"""

dist_delay_corr = df[['distance', 'dep_delay', 'arr_delay']].corr().round(3)
display(dist_delay_corr)

dist_band_delay = (
    df.groupby('distance_band', observed=True)
    .agg(
        flight_count=('dep_delay', 'count'),
        avg_dep_delay=('dep_delay', 'mean'),
        median_dep_delay=('dep_delay', 'median'),
        on_time_pct=('is_on_time', lambda x: round(x.mean() * 100, 2))
    )
    .round(2)
)
display(dist_band_delay)

"""Short-haul vs long-haul"""

flight_type_delay = df.groupby('flight_type')['dep_delay'].mean().round(2)
display(flight_type_delay)

"""Most at-risk specific flights"""

most_at_risk = (
    df[df['op_unique_carrier'].notna()]
    .groupby(['op_unique_carrier', 'op_carrier_fl_num', 'origin', 'dest'])['total_delay']
    .mean()
    .round(2)
    .sort_values(ascending=False)
)
display(most_at_risk.head(20))

"""Diverted flights"""

diversion_counts = (
    df[df['diverted'] == 1]
    .groupby(['origin', 'dest'])
    .size()
    .sort_values(ascending=False)
    .rename('diversion_count')
    .head(20)
)
display(diversion_counts)

"""**SECTION 10: VISUALISATIONS**"""

fig_kw = dict(figsize=(12, 6), dpi=120)

"""On-Time Performance % by Carrier"""

fig, ax = plt.subplots(**fig_kw)
otp_by_carrier.sort_values().plot(
    kind='barh', ax=ax,
    color=['#c0392b' if v < 75 else '#e67e22' if v < 85 else '#27ae60'
           for v in otp_by_carrier.sort_values()]
)
ax.set_title('On-Time Arrival Performance by Carrier (arr_delay ≤ 15 min)', fontsize=14, fontweight='bold')
ax.set_xlabel('On-Time %')
ax.axvline(otp_by_carrier.mean(), color='navy', linestyle='--', linewidth=1.2,
           label=f'Average ({otp_by_carrier.mean():.1f}%)')
ax.legend()
for bar, val in zip(ax.patches, otp_by_carrier.sort_values()):
    ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
            f'{val:.1f}%', va='center', fontsize=9)
plt.tight_layout()
plt.show()

"""Delay Cause: Frequency vs Severity"""

fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=120)
delay_cause_counts.sort_values().plot(kind='barh', ax=axes[0], color='steelblue')
axes[0].set_title('Flights Affected', fontsize=13, fontweight='bold')
axes[0].set_xlabel('Number of Flights')
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
avg_delay_by_cause.sort_values().plot(kind='barh', ax=axes[1], color='coral')
axes[1].set_title('Avg Minutes Contributed', fontsize=13, fontweight='bold')
axes[1].set_xlabel('Avg Delay (minutes)')
plt.suptitle('Delay Causes: Frequency vs Severity', fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plt.show()

"""Monthly Avg Delay Trend"""

fig, ax = plt.subplots(**fig_kw)
plot_monthly = avg_delay_by_month.copy()
plot_monthly.index = plot_monthly.index.map(lambda m: pd.Timestamp(2024, m, 1).strftime('%b'))
ax.plot(plot_monthly.index, plot_monthly.values,
        marker='o', color='steelblue', linewidth=2.2, markersize=7)
ax.fill_between(plot_monthly.index, plot_monthly.values, alpha=0.15, color='steelblue')
ax.axhline(plot_monthly.mean(), linestyle='--', color='grey', linewidth=1,
           label=f'Annual average ({plot_monthly.mean():.1f} min)')
ax.set_title('Average Departure Delay by Month', fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Avg Departure Delay (min)')
ax.legend()
plt.tight_layout()
plt.show()

"""Delay Heatmap: Hour of Day × Day of Week"""

heatmap_data = (
    df.groupby(['day_of_week', 'scheduled_departure_hour'])['dep_delay']
    .mean()
    .unstack()
    .round(1)
)
heatmap_data.index = [day_names[d] for d in heatmap_data.index]
fig, ax = plt.subplots(figsize=(16, 5), dpi=120)
sns.heatmap(heatmap_data, cmap='YlOrRd', linewidths=0.3, ax=ax,
            cbar_kws={'label': 'Avg Dep Delay (min)'})
ax.set_title('Avg Departure Delay by Hour × Day of Week', fontsize=14, fontweight='bold')
ax.set_xlabel('Scheduled Departure Hour')
ax.set_ylabel('')
plt.tight_layout()
plt.show()

"""Airport Congestion Score by Hour"""

fig, ax = plt.subplots(**fig_kw)
ax.plot(congestion_by_hour.index, congestion_by_hour['congestion_score'],
        marker='o', color='darkorange', linewidth=2.2, markersize=6)
ax.fill_between(congestion_by_hour.index, congestion_by_hour['congestion_score'],
                alpha=0.15, color='darkorange')
ax.set_title('Airport Congestion Score by Hour\n(Avg Taxi-Out + Avg NAS Delay)',
             fontsize=13, fontweight='bold')
ax.set_xlabel('Scheduled Departure Hour')
ax.set_ylabel('Congestion Score (min)')
ax.set_xticks(congestion_by_hour.index)
plt.tight_layout()
plt.show()

"""Schedule Padding Effectiveness"""

fig, ax = plt.subplots(**fig_kw)
padding_vs_otp['on_time_pct'].plot(
    kind='bar', ax=ax, edgecolor='white',
    color=['#c0392b' if v < 70 else '#e67e22' if v < 80 else '#27ae60'
           for v in padding_vs_otp['on_time_pct']]
)
ax.set_title('On-Time Arrival % by Schedule Padding Category', fontsize=14, fontweight='bold')
ax.set_xlabel('')
ax.set_ylabel('On-Time %')
ax.set_xticklabels(ax.get_xticklabels(), rotation=25, ha='right')
for bar, val in zip(ax.patches, padding_vs_otp['on_time_pct']):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3,
            f'{val:.1f}%', ha='center', fontsize=9)
plt.tight_layout()
plt.show()

"""Cancellation Rate by Carrier"""

if 'cancelled' in df.columns:
    fig, ax = plt.subplots(**fig_kw)
    cancellation_by_carrier['cancellation_rate_pct'].sort_values().plot(
        kind='barh', ax=ax, color='salmon', edgecolor='white'
    )
    ax.axvline(cancellation_by_carrier['cancellation_rate_pct'].mean(), linestyle='--',
               color='navy', linewidth=1.2,
               label=f"Average ({cancellation_by_carrier['cancellation_rate_pct'].mean():.2f}%)")
    ax.set_title('Cancellation Rate by Carrier', fontsize=14, fontweight='bold')
    ax.set_xlabel('Cancellation Rate (%)')
    ax.legend()
    plt.tight_layout()
    plt.show()

"""Distance Band vs On-Time Performance"""

fig, ax = plt.subplots(**fig_kw)
dist_otp = dist_band_delay['on_time_pct']
dist_otp.plot(kind='bar', ax=ax, color='mediumseagreen', edgecolor='white', label='On-Time %')
ax.set_title('On-Time Performance & Avg Delay by Flight Distance Band',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Distance Band')
ax.set_ylabel('On-Time Arrival %')
ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha='right')
ax2 = ax.twinx()
dist_band_delay['avg_dep_delay'].plot(
    ax=ax2, color='steelblue', marker='D', linewidth=2, markersize=7, label='Avg Dep Delay')
ax2.set_ylabel('Avg Departure Delay (min)', color='steelblue')
ax2.tick_params(axis='y', labelcolor='steelblue')
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='lower right')
plt.tight_layout()
plt.show()

"""**SECTION 11: SUMMARY OF KEY FINDINGS**"""

best_carrier_otp = otp_by_carrier.idxmax()
worst_carrier_otp = otp_by_carrier.idxmin()
most_congested = congestion_score['congestion_score'].idxmax()
peak_delay_hour = avg_delay_by_hour.idxmax()
best_delay_hour = avg_delay_by_hour.idxmin()
worst_season = avg_delay_by_season.idxmax()
best_season = avg_delay_by_season.idxmin()
top_catch_up = catch_up_factor.idxmax()
top_delay_cause = delay_cause_counts.idxmax()

cancel_line = ''
if 'cancelled' in df.columns:
    worst_cancel = cancellation_by_carrier['cancellation_rate_pct'].idxmax()
    cancel_line  = f"  Highest cancellation rate    : {worst_cancel}  ({cancellation_by_carrier.loc[worst_cancel, 'cancellation_rate_pct']:.2f}%)\n"

print("\n" + "=" * 60)
print("  KEY FINDINGS — FLIGHT DATA 2024")
print("=" * 60)
print(f"""
CARRIERS
  Best on-time performance   : {best_carrier_otp}  ({otp_by_carrier[best_carrier_otp]:.1f}%)
  Worst on-time performance  : {worst_carrier_otp}  ({otp_by_carrier[worst_carrier_otp]:.1f}%)
  Best catch-up factor       : {top_catch_up}  ({catch_up_factor[top_catch_up]:.1%} of late-departing flights still arrive on time)
{cancel_line}
AIRPORTS
  Most congested airport     : {most_congested}  (score: {congestion_score.loc[most_congested, 'congestion_score']:.1f} min)
  Busiest departure airport  : {busiest_airports.idxmax()}  ({busiest_airports.max():,} flights)

DELAYS
  Most common delay cause    : {top_delay_cause}  ({delay_cause_counts[top_delay_cause]:,} flights affected)
  Peak delay hour            : {peak_delay_hour}:00  (avg {avg_delay_by_hour[peak_delay_hour]:.1f} min departure delay)
  Best departure hour        : {best_delay_hour}:00  (avg {avg_delay_by_hour[best_delay_hour]:.1f} min departure delay)
  Worst season for delays    : {worst_season}  (avg {avg_delay_by_season[worst_season]:.1f} min)
  Best season for delays     : {best_season}  (avg {avg_delay_by_season[best_season]:.1f} min)

DATA QUALITY NOTES
  Outlier flights (>p99)     : {outlier_count:,} ({outlier_pct:.2f}% of dataset)
  Cause-of-delay null fill   : {', '.join(DELAY_COLS)}
  All averages above include outliers — see Section 3 for outlier-adjusted figures.
""")
