import logging
import requests
from time import sleep

from kalliope.core.NeuronModule import (
    NeuronModule,
    MissingParameterException,
    InvalidParameterException,
)

logging.basicConfig()
logger = logging.getLogger("kalliope")

Spotify_Actions = (
    "ADD",
    "CURRENT",
    "NEXT",
    "LOAD",
    "PAUSE",
    "PREV",
    "SET_VOLUME",
    "VOLUME_DOWN",
    "VOLUME_UP",
)

Search_Types = {
    "AUTO": "topHit",
    "TRACK": "tracks",
    "ALBUM": "albums",
    "PLAYLIST": "playlists",
    "ARTIST": "artists",
}


class Spotify(NeuronModule):
    def __init__(self, **kwargs):
        actions = (
            self.add,
            self.current,
            self.next,
            self.load,
            self.pause,
            self.prev,
            self.set_volume,
            self.volume_down,
            self.volume_up,
        )

        super(Spotify, self).__init__(**kwargs)

        self.action = kwargs.get("action")

        self.ip = kwargs.get("ip", "127.0.0.1")
        self.port = kwargs.get("port", 24879)
        self.ignore_exceptions = kwargs.get("ignore_exceptions", True)
        self.retries = kwargs.get("retries", 3)
        self.retry_delay = kwargs.get("retry_delay", 1)

        self.query = kwargs.get("query")  # for ADD and LOAD
        self.search_type = kwargs.get("search_type", "AUTO")  # for LOAD
        self.pause_state = kwargs.get("pause_state")  # for PAUSE
        self.volume = kwargs.get("volume")  # for SET_VOLUME

        if self._is_parameters_ok():
            self.api = LibrespotJavaApi(
                self.ip, self.port, retries=self.retries, retry_delay=self.retry_delay
            )
            action = actions[Spotify_Actions.index(self.action)]
            self.message = {"success": False}
            try:
                action()
            except Exception as e:
                logger.error(e)
                if not self.ignore_exceptions:
                    raise

            self.say(self.message)

    def _search(self):
        if not self._is_search_parameters_ok():
            return
        try:
            result = self.api.search(self.query)["results"][
                Search_Types[self.search_type]
            ]["hits"][0]
        except (KeyError, IndexError):
            return {}
        return self._format_search_result(result)

    @staticmethod
    def _format_search_result(result):
        uri = result["uri"]
        name = result["name"]
        if "artists" in result:
            artists = [i["name"] for i in result["artists"]]
            name = ", ".join(artists) + " - " + name
        return {"uri": uri, "name": name}

    def add(self):
        self.message["name"] = None

        self.search_type = "TRACK"
        result = self._search()
        if not result:
            return

        self.api.player_add_to_queue(result["uri"])

        self.message["success"] = True
        self.message["name"] = result["name"]

    def current(self):
        self.message["name"] = None

        current = self.api.player_current()
        if not current:
            return

        self.message["success"] = True
        self.message["name"] = self._name_from_current(current)

    @staticmethod
    def _name_from_current(current):
        artists = [i["name"] for i in current["track"]["album"]["artist"]]
        name = ", ".join(artists) + " - " + current["track"]["name"]
        return name

    def next(self):
        self.api.player_next()
        self.message["success"] = True

    def load(self):
        self.message["name"] = None

        result = self._search()
        if not result:
            return message

        self.api.player_load(result["uri"], True)

        self.message["success"] = True
        self.message["name"] = result["name"]

    def pause(self):
        if self.pause_state is None:  # toggle play/pause
            self.api.player_play_pause()
        if self.pause_state is True:
            self.api.player_pause()
        if self.pause_state is False:
            self.api.player_resume()

        self.message["success"] = True

    def prev(self):
        self.api.player_prev()
        self.message["success"] = True

    def set_volume(self):
        if not self._is_volume_parameters_ok():
            return
        value = self._convert_volume(self.volume)

        self.api.player_set_volume(value)

        self.message["success"] = True

    def volume_down(self):
        self.api.player_volume_down()
        self.message["success"] = True

    def volume_up(self):
        self.api.player_volume_up()
        self.message["success"] = True

    @staticmethod
    def _convert_volume(value):
        """Percentage to value from 0 to 65536"""
        value = int(value)
        max = 65536
        return int(value / 100 * max)

    def _is_parameters_ok(self):
        if self.action is None:
            raise MissingParameterException("Spotify needs an action parameter")
        if self.action not in Spotify_Actions:
            raise InvalidParameterException("Invalid action parameter")

        return True

    def _is_search_parameters_ok(self):
        if self.query is None:
            raise MissingParameterException(
                self.action + " action needs a query parameter"
            )
        if self.search_type not in Search_Types:
            raise InvalidParameterException("Invalid search_type parameter")

        return True

    def _is_volume_parameters_ok(self):
        if self.volume is None:
            raise MissingParameterException(
                self.action + " action needs a volume parameter"
            )
        try:
            value = int(self.volume)
        except ValueError:
            raise InvalidParameterException("volume parameter must be integer 0..100")
        if value < 0 or value > 100:
            raise InvalidParameterException("volume parameter must be integer 0..100")

        return True


class LibrespotJavaApi:
    def __init__(
        self, ip="127.0.0.1", port=24879, retries=3, retry_delay=1, session=None
    ):
        if not session:
            session = requests.Session()
        self.session = session

        self.url = "http://{0}:{1}/".format(ip, port)

        self.retries = retries
        self.retry_delay = retry_delay

    def _post(self, endpoint, data=None):
        retries = self.retries
        while True:
            logger.debug("POST {0}{1} data={2}".format(self.url, endpoint, data))
            try:
                response = self.session.post(self.url + endpoint, data=data)
                logger.debug(str(response.status_code) + ": " + response.text)
                if not response.status_code == 200:
                    raise ApiException(response.status_code, response.reason)
            except Exception as e:
                if retries == 0:
                    raise
                logger.info("RETRY: " + str(e))
                retries -= 1
                sleep(self.retry_delay)
                continue
            return response

    def player_load(self, uri, play=False) -> None:
        """Load a track from a given URI"""
        self._post("player/load", {"uri": uri, "play": play})

    def player_play_pause(self) -> None:
        """Toggle play/pause status"""
        self._post("player/play-pause")

    def player_pause(self) -> None:
        """Pause playback"""
        self._post("player/pause")

    def player_resume(self) -> None:
        """Resume playback"""
        self._post("player/resume")

    def player_next(self) -> None:
        """Skip to next track"""
        self._post("player/next")

    def player_prev(self) -> None:
        """Skip to previous track"""
        self._post("player/prev")

    def player_seek(self, pos) -> None:
        """Seek to a given position in ms specified by pos"""
        self._post("player/seek", {"pos": pos})

    def player_set_volume(self, volume) -> None:
        """Set volume to a given volume value from 0 to 65536"""
        self._post("player/set-volume", {"volume": volume})

    def player_volume_up(self) -> None:
        """Up the volume a little bit"""
        self._post("player/volume-up")

    def player_volume_down(self) -> None:
        """Lower the volume a little bit"""
        self._post("player/volume-down")

    def player_current(self) -> dict:
        """Retrieve information about the current track (metadata and time)"""
        return self._post("player/current").json()

    def player_tracks(self, with_queue=False) -> dict:
        """Retrieve all the tracks in the player state with metadata,
        you can specify withQueue"""
        return self._post("player/tracks", {"withQueue": with_queue}).json()

    def player_add_to_queue(self, uri) -> None:
        """Add a track to the queue, specified by uri"""
        self._post("player/addToQueue", {"uri": uri})

    def player_remove_from_queue(self, uri) -> None:
        """Remove a track from the queue, specified by uri"""
        self._post("player/removeFromQueue", {"uri": uri})

    def metadata(self, uri, type=None) -> dict:
        """Retrieve metadata. type can be one of episode, track, album,
        show, artist or playlist, uri is the standard Spotify uri"""
        if type:
            endpoint = "metadata/{0}/{1}".format(type, uri)
        else:
            endpoint = "metadata/{0}".format(uri)
        return self._post(endpoint).json()

    def search(self, query) -> dict:
        """Make a search"""
        return self._post("search/{0}".format(query)).json()

    def token(self, scope) -> dict:
        """Request an access token for a specific scope (or a comma separated list of scopes)"""
        return self._post("token/{0}".format(scope)).json()

    def profile_followers(self, user_id) -> list:
        """Retrieve a list of profiles that are followers of the specified user"""
        return self._post("profile/{0}/followers".format(user_id)).json()["profiles"]

    def profile_following(self, user_id) -> list:
        """Retrieve a list of profiles that the specified user is following"""
        return self._post("profile/{0}/following".format(user_id)).json()["profiles"]


class ApiException(Exception):
    def __init__(self, code, message):
        self.code = code
        if self.code == 204:
            message = "There isn't any active session"
        if self.code == 500:
            message = "The session is invalid"
        if self.code == 503:
            message = "The session is reconnecting"
        self.message = message

    def __str__(self):
        return "{0}: {1}".format(self.code, self.message)
