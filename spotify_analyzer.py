import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from datetime import datetime
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spotify API credentials
CLIENT_ID = "3652b936c426424089ad33db68940d5a"
CLIENT_SECRET = "dd3fb89cac0a4f8bbb195df2c8057f7e"
REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "playlist-read-private playlist-read-collaborative user-library-read user-read-private user-read-email playlist-modify-public playlist-modify-private"

class SpotifyAnalyzer:
    def __init__(self):
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_path=".cache"
            ))
            token = self.sp.auth_manager.get_access_token(as_dict=False)
            logger.info(f"Initialized Spotify client. Access token: {token[:10]}...")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {str(e)}")
            raise

    def get_playlist_id(self, url):
        try:
            logger.info(f"Extracting playlist ID from {url}")
            return url.split('/')[-1].split('?')[0]
        except Exception as e:
            logger.error(f"Error extracting playlist ID: {str(e)}")
            raise

    def get_user_profile(self, user_id):
        try:
            logger.info(f"Fetching profile for user ID: {user_id}")
            profile = self.sp.user(user_id)
            return {
                "display_name": profile.get("display_name"),
                "external_urls": profile.get("external_urls", {}).get("spotify"),
                "followers": profile.get("followers", {}).get("total", 0),
                "href": profile.get("href"),
                "id": profile.get("id"),
                "images": [{"url": img["url"], "height": img["height"], "width": img["width"]} 
                          for img in profile.get("images", [])],
                "type": profile.get("type"),
                "uri": profile.get("uri")
            }
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return {}

    def get_artist_details(self, artist_ids):
        try:
            logger.info(f"Fetching artist details for artist_ids: {artist_ids}, type: {type(artist_ids)}")
            artists = self.sp.artists(artist_ids)
            return [{
                "artist_id": artist["id"],
                "artist_name": artist["name"],
                "artist_popularity": artist["popularity"],
                "artist_genres": artist["genres"],
                "artist_followers": artist["followers"]["total"]
            } for artist in artists["artists"]]
        except Exception as e:
            logger.error(f"Error fetching artist details: {str(e)}")
            return []

    def get_album_details(self, album_id):
        try:
            album = self.sp.album(album_id)
            return {
                "album_id": album["id"],
                "album_name": album["name"],
                "album_popularity": album.get("popularity", 0),
                "album_label": album.get("label", ""),
                "album_copyrights": [c["text"] for c in album.get("copyrights", [])]
            }
        except Exception as e:
            logger.error(f"Error fetching album details: {str(e)}")
            return {}

    def get_audio_analysis_summary(self, track_id):
        """
        Fetches audio analysis data for a given track ID.
        
        Args:
            track_id (str): The Spotify track ID.
        
        Returns:
            dict: A dictionary containing audio analysis data or None for each field if the request fails.
        """
        try:
            # Attempt to fetch audio analysis data using the Spotify API
            analysis = self.sp.audio_analysis(track_id)
            
            # Extract relevant fields from the analysis
            return {
                "track_id": track_id,
                "tempo_confidence": analysis["track"]["tempo_confidence"],
                "key_confidence": analysis["track"]["key_confidence"],
                "mode_confidence": analysis["track"]["mode_confidence"],
                "time_signature_confidence": analysis["track"]["time_signature_confidence"],
                "num_segments": len(analysis["segments"]),
                "num_bars": len(analysis["bars"]),
                "num_beats": len(analysis["beats"])
            }
        except Exception as e:
            # Log the error for troubleshooting
            logger.error(f"Error fetching audio analysis for {track_id}: {str(e)}")
            
            # Return default values (None) for all fields if the request fails
            return {
                "track_id": track_id,
                "tempo_confidence": None,
                "key_confidence": None,
                "mode_confidence": None,
                "time_signature_confidence": None,
                "num_segments": None,
                "num_bars": None,
                "num_beats": None
            }

    def get_playlist_data(self, playlist_url):
        try:
            playlist_id = self.get_playlist_id(playlist_url)
            logger.info(f"Fetching playlist data for ID: {playlist_id}")
            
            # Refresh token
            self.sp.auth_manager.get_access_token(as_dict=False)
            
            playlist = self.sp.playlist(playlist_id, market="US")
            logger.info(f"Playlist name: {playlist['name']}, tracks: {playlist['tracks']['total']}")
            
            owner_profile = self.get_user_profile(playlist["owner"]["id"])
            
            tracks = []
            track_ids = []
            results = self.sp.playlist_items(playlist_id, additional_types=('track',))
            
            while results:
                for item in results['items']:
                    track = item['track']
                    if track and track['id']:
                        artist_details = self.get_artist_details([track['artists'][0]['id']])
                        album_details = self.get_album_details(track['album']['id'])
                        audio_analysis = self.get_audio_analysis_summary(track['id'])

                        track_data = {
                            # Playlist metadata
                            "playlist_name": playlist['name'],
                            "playlist_id": playlist['id'],
                            "playlist_description": playlist.get('description', ''),
                            "playlist_followers": playlist['followers']['total'],
                            "playlist_public": playlist['public'],
                            "playlist_collaborative": playlist['collaborative'],
                            "playlist_snapshot_id": playlist['snapshot_id'],
                            "playlist_external_url": playlist["external_urls"]["spotify"],
                            "playlist_images": [{"url": img["url"], "height": img["height"], "width": img["width"]} 
                                              for img in playlist.get("images", [])],
                            # Owner profile
                            "owner_display_name": owner_profile.get("display_name"),
                            "owner_id": owner_profile.get("id"),
                            "owner_external_url": owner_profile.get("external_urls"),
                            "owner_followers": owner_profile.get("followers"),
                            "owner_href": owner_profile.get("href"),
                            "owner_images": owner_profile.get("images", []),
                            "owner_type": owner_profile.get("type"),
                            "owner_uri": owner_profile.get("uri"),
                            # Track metadata
                            "track_name": track['name'],
                            "track_id": track['id'],
                            "artists": ", ".join([artist['name'] for artist in track['artists']]),
                            "artist_ids": [artist['id'] for artist in track['artists']],
                            "album_name": track['album']['name'],
                            "album_id": track['album']['id'],
                            "album_type": track['album']['album_type'],
                            "album_release_date": track['album']['release_date'],
                            "album_release_date_precision": track['album']['release_date_precision'],
                            "album_total_tracks": track['album']['total_tracks'],
                            "album_external_url": track['album']['external_urls']['spotify'],
                            "duration_ms": track['duration_ms'],
                            "popularity": track['popularity'],
                            "explicit": track['explicit'],
                            "added_at": item['added_at'],
                            "is_local": track['is_local'],
                            "preview_url": track.get('preview_url'),
                            "track_number": track['track_number'],
                            "disc_number": track['disc_number'],
                            "available_markets": track['available_markets'],
                            "external_ids": track.get('external_ids', {}),
                            "track_external_url": track['external_urls']['spotify'],
                            # Artist details (primary artist)
                            "artist_popularity": artist_details[0]["artist_popularity"] if artist_details else 0,
                            "artist_genres": artist_details[0]["artist_genres"] if artist_details else [],
                            "artist_followers": artist_details[0]["artist_followers"] if artist_details else 0,
                            # Album details
                            "album_popularity": album_details.get("album_popularity", 0),
                            "album_label": album_details.get("album_label", ""),
                            "album_copyrights": album_details.get("album_copyrights", []),
                            # Audio analysis data
                            "tempo_confidence": audio_analysis.get("tempo_confidence"),
                            "key_confidence": audio_analysis.get("key_confidence"),
                            "mode_confidence": audio_analysis.get("mode_confidence"),
                            "time_signature_confidence": audio_analysis.get("time_signature_confidence"),
                            "num_segments": audio_analysis.get("num_segments"),
                            "num_bars": audio_analysis.get("num_bars"),
                            "num_beats": audio_analysis.get("num_beats")
                        }
                        tracks.append(track_data)
                        track_ids.append(track['id'])
                
                if results['next']:
                    results = self.sp.next(results)
                else:
                    results = None
                time.sleep(0.5)

            logger.info(f"Collected {len(track_ids)} track IDs. Fetching audio features...")
            audio_features = []
            try:
                for i in range(0, len(track_ids), 100):
                    batch = track_ids[i:i+100]
                    features = self.sp.audio_features(batch)
                    if features:
                        audio_features.extend([f for f in features if f])
                    logger.info(f"Fetched features for batch {i//100 + 1}")
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Batch audio features fetch failed: {str(e)}. Falling back to individual fetches.")
                for track_id in track_ids:
                    try:
                        features = self.sp.audio_features([track_id])
                        if features and features[0]:
                            audio_features.append(features[0])
                        else:
                            audio_features.append(None)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error fetching audio features for {track_id}: {str(e)}")
                        audio_features.append(None)

            df_tracks = pd.DataFrame(tracks)
            df_features = pd.DataFrame([f for f in audio_features if f])
            
            if not df_features.empty:
                feature_columns = ['id', 'danceability', 'energy', 'key', 'loudness', 'mode', 
                                 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 
                                 'valence', 'tempo', 'time_signature']
                df_features = df_features[feature_columns]
                df = pd.merge(df_tracks, df_features, left_on='track_id', right_on='id', how='left')
                df = df.drop(columns=['id'])
            else:
                logger.warning("No audio features retrieved. Using track metadata only.")
                df = df_tracks

            df['added_at'] = pd.to_datetime(df['added_at'])
            logger.info(f"Dataframe created with {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Error in get_playlist_data: {str(e)}")
            raise

    def save_to_csv(self, df, filename):
        try:
            df.to_csv(filename, index=False)
            logger.info(f"Saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        analyzer = SpotifyAnalyzer()
        playlist_url = "https://open.spotify.com/playlist/5wVl2MwWDgNXNCFBlXzOc0?si=5fb5f7e2a9a74be5"
        df = analyzer.get_playlist_data(playlist_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analyzer.save_to_csv(df, f"playlist_data_{timestamp}.csv")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")