import pandas as pd

df = pd.read_csv('/Users/jeffersonsuh/jeffersonsuh.github.io/spotifyanalyzer/playlist_data_20250224_155646.csv')

df['release_year'] = df['album_release_date'].str[:4]

df_by_year = df[['release_year', 'track_name']].groupby('release_year').count().sort_values('track_name', ascending=False).reset_index()
df_by_year.columns = ['release_year', 'track_count']

print("Top years by track count:")
print(df_by_year)

#df_by_year.to_csv('tracks_by_release_year.csv', index=False)
#print("\nFull table saved to 'tracks_by_release_year.csv'")