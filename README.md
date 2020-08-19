# kalliope_neuron_spotify
A Kalliope neuron used to communicate with local Spotify client. Provides integration with the [API](https://github.com/librespot-org/librespot-java/tree/dev/api) of [Librespot-Java](https://github.com/librespot-org/librespot-java). **Requires premium account.**

## Synopsis
Make kalliope play Spotify music and control playback.

## Installation
The solution is based on [SpoCon](https://github.com/spocon/spocon), the easiest way to run a Spotify client as a service.

### Easy installation
```bash
kalliope install --git-url https://github.com/raitonoberu/kalliope_neuron_spotify.git
```

### Manual installation
```bash
sudo pip3 install --upgrade requests
curl -sL https://spocon.github.io/spocon/install.sh | sh
# enter your kalliope folder
cd resources/neurons
git clone https://github.com/raitonoberu/kalliope_neuron_spotify
mv kalliope_neuron_spotify spotify
```

## Configuration
After installation, you must configure SpoCon:
```bash
sudo nano /opt/spocon/config.toml
```

Set the authentication strategy to "USER_PASS" and set your username and password. **Find the username in [your account settings](https://www.spotify.com/account/overview/)**.
```toml
# ...
[auth]
strategy = "USER_PASS"
username = "<your username>"
password = "<your password>"
# ...
```
More about the configuration [here](https://github.com/spocon/spocon/blob/master/README.md#configuration).

Now you have to restart SpoCon service:
```bash
sudo systemctl restart spocon
```

## Options
| Parameter   | Required                      | Default     | Choices                                        | comment                                                              |
|-------------|-------------------------------|-------------|------------------------------------------------|----------------------------------------------------------------------|
| action      | yes                           |             | [Actions](#actions)                            | The action to do with Spotify                                        |
| ip          | no                            | "127.0.0.1" | str                                            | IP address of the computer running SpoCon                            |
| port        | no                            | 24879       | int                                            | API port defined in /opt/spocon/config.toml                          |
| retries     | no                            | 3           | int                                            | Number of retries to connect to the client                           |
| retry_delay | no                            | 1           | int                                            | Delay between connection attempts (secs)                             |
| query       | yes (for a couple of actions) |             | str                                            | Search query                                                         |
| search_type | no                            | "AUTO"      | "AUTO", "TRACK", "ALBUM", "PLAYLIST", "ARTIST" | The type of search result                                            |
| pause_state | no                            | None        | bool                                           | Stops playback if True. Resumes if False. Toggles play/pause if None |

### Actions
| Name           | Description                             | Parameters           | Return values |
|----------------|-----------------------------------------|----------------------|---------------|
| ADD            | Add search result to queue              | query                | success, name |
| CURRENT        | Retrieve name of the current track      |                      | success, name |
| NEXT           | Play the next track                     |                      | success       |
| LOAD           | Play search result immediately          | query, [search_type] | success, name |
| PAUSE          | Toggle play/pause                       | pause_state          | success       |
| PREV           | Play the previous track                 |                      | success       |
| SET_VOLUME     | Set the volume to a specified percentage| volume               | success       |
| VOLUME_DOWN    | Lower the volume a little bit           |                      | success       |
| VOLUME_UP      | Up the volume a little bit              |                      | success       |

### Return values
| Name    | Description                         | Type | Sample                           |
|---------|-------------------------------------|------|----------------------------------|
| success | Was the request successful          | bool | True                             |
| name    | Name of the track (found / current) | str  | "Rick Astley - Together Forever" |

## Synapses example
```yaml
- name:                "spotify-current"
  signals:
    - order:           "what is playing"
  neurons:
    - spotify:
         action:       "CURRENT"
         say_template:
           - "{{ name if success else 'Nothing playing' }}"

- name:                "spotify-pause"
  signals:
    - order:           "pause"
  neurons:
    - spotify:
         action:       "PAUSE"

- name:                "load"
  signals:
    - order:           "turn on {{ query }}"
  neurons:
    - spotify:
        action:        "LOAD"
        query:         "{{ query }}"
        say_template:
           - "{{ 'Ok' if success else 'Nothing found' }}"
```
