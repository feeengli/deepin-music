

#ifndef VLCQT_MEDIAPLAYER_H_
#define VLCQT_MEDIAPLAYER_H_

#include <QtCore/QObject>
#include <QtCore/QString>
#include <QtGui/qwindowdefs.h>

#include "Enums.h"
//#include "SharedExportCore.h"

#define LIBVLC_VERSION 0x020200

class VlcAudio;
class VlcEqualizer;
class VlcInstance;
class VlcMedia;
class VlcVideo;
class VlcVideoDelegate;

struct libvlc_event_t;
struct libvlc_event_manager_t;
struct libvlc_media_t;
struct libvlc_media_player_t;


class VLCQT_CORE_EXPORT VlcMediaPlayer : public QObject
{
    Q_OBJECT
public:
    /*!
        \brief VlcMediaPlayer constructor.

        This is mandatory to use libvlc playback functions.

        \param instance instance object (VlcInstance *)
    */
    explicit VlcMediaPlayer(VlcInstance *instance);

    /*!
        VlcMediaPlayer destructor
    */
    ~VlcMediaPlayer();

    /*!
        \brief Returns libvlc media player object.
        \return libvlc media player (libvlc_media_player_t *)
    */
    libvlc_media_player_t *core() const;

    /*!
        \brief Returns audio manager object.
        \return audio manager (VlcAudio *)
    */
//    VlcAudio *audio() const;

#if LIBVLC_VERSION >= 0x020200
    /*!
        \brief Returns equalizer object.
        \return equalizer (VlcEqualizer *)
    */
    VlcEqualizer *equalizer() const;
#endif

    /*!
        \brief Get the current movie length (in ms).
        \return the movie length (in ms), or -1 if there is no media (const int)
    */
    int length() const;

    /*!
        \brief Get current media object
        \return media object (VlcMedia *)
    */
    //VlcMedia *currentMedia() const;

    /*!
        \brief Get current media core object
        \return media core object (libvlc_media_t *)
    */
    //libvlc_media_t *currentMediaCore();

    /*!
        \brief Open media file or stream. Any media should be playable and opened.
        \param media object (VlcMedia *)
    */
    void open(VlcMedia *media);

    /*!
        \brief Just opens the media file or stream, do not starts playing the media.
        \param media object (VlcMedia *)
    */
    //void openOnly(VlcMedia *media);

    /**
     * @brief releaseMediaPlayer 释放vlc资源
     */
    void initCddaTrack();

public slots:
    /*! \brief Set the movie time (in ms).

        This has no effect if no media is being played. Not all formats and protocols support this.

        \param time the movie time (in ms) (int)
    */
    void setTime(qint64 time);

public:
    /*!
        \brief Get the current movie time (in ms).
        \return the movie time (in ms), or -1 if there is no media (const int)
    */
    int time() const;

    /*! \brief Set video widget.

        Set video widget to be able to play video inside Qt interface.

        \param widget video widget (VlcVideoDelegate *)
    */
//    void setVideoWidget(VlcVideoDelegate *widget);

    /*!
        \brief Get video output status
        \return video output status (const bool)
    */
    //bool hasVout() const;

    /*!
        \brief Get seekable status
        \return seekable status (const bool)
    */
    //bool seekable() const;

    /*!
        \brief Get current player state.
        \return current player state (const Vlc::State)
    */
    Vlc::State state() const;

    /*!
        \brief Get current video widget.
        \return current video widget (VlcVideoWidget *)
    */
//    VlcVideoDelegate *videoWidget() const;

    /*!
        \brief Get media content position.
        \return current media position (float)
    */
    float position();

    /*!
        \brief Get sample aspect ratio for current video track( vlc >= 2.1.0 ).
        \return sample aspect ratio (float)
    */
    //float sampleAspectRatio();

    /*!
        \brief Get current media playback rate.
        \return current media playback rate (float)
    */
    //float playbackRate();

public slots:
    /*! \brief Set the media position.

        This has no effect if no media is being played. Not all formats and protocols support this.

        \param pos the media position (float)
    */
    void setPosition(float pos);

    /*! \brief Set the media playback rate.

        \param rate the media playback rate (float)
    */
    //void setPlaybackRate(float rate);

    /*!
        \brief Starts playing current media if possible
    */
    void play();

    /*!
        \brief Pauses the playback of current media if possible
    */
    void pause();

    /*!
        \brief Toggles pause of the playback of current media if possible
    */
    //timePropertyWidthvoid togglePause();

    /*!
        \brief Resumes the playback of current media if possible
    */
    void resume();

    /*!
        \brief Stops playing current media
    */
    void stop();

//    void timeoutSlot();

signals:
    /*!
        \brief Signal sent on backward
    */
    void backward();

    /*!
        \brief Signal sent on buffering
        \param buffer buffer status in percent
    */
    void buffering(float buffer);

    /*!
        \brief Signal sent on buffering
        \param buffer buffer status in percent
    */
    void buffering(int buffer);

    /*!
        \brief Signal sent when end reached
    */
    void end();

    /*!
        \brief Signal sent on error
    */
    void error();

    /*!
        \brief Signal sent on forward
    */
    void forward();

    /*!
        \brief Signal sent on length change
        \param length new length
    */
    void lengthChanged(int length);

    /*!
        \brief Signal sent on media change
        \param media new media object
    */
    void mediaChanged(libvlc_media_t *media);

    /*!
        \brief Signal sent nothing speciall happened
    */
    void nothingSpecial();

    /*!
        \brief Signal sent when opening
    */
    void opening();

    /*!
        \brief Signal sent on pausable change
        \param pausable pausable status
    */
    void pausableChanged(bool pausable);

    /*!
        \brief Signal sent when paused
    */
    void paused();

    /*!
        \brief Signal sent when playing
    */
    void playing();

    /*!
        \brief Signal sent on position change
        \param position new position
    */
    void positionChanged(float position);

    /*!
        \brief Signal sent on seekable change
        \param seekable seekable status
    */
    void seekableChanged(bool seekable);

    /*!
        \brief Signal sent on snapshot taken
        \param filename filename of the snapshot
    */
    void snapshotTaken(const QString &filename);

    /*!
        \brief Signal sent when stopped
    */
    void stopped();

    /*!
        \brief Signal sent on time change
        \param time new time
    */
    void timeChanged(qint64 time);

    /*!
        \brief Signal sent on title change
        \param title new title
    */
    void titleChanged(int title);

    /*!
        \brief Signal sent when video output is available
        \param count number of video outputs available
    */
    void vout(int count);

    /*!
        \brief Signal sent when state of the player changed
    */
    void stateChanged();

private:
    static void libvlc_callback(const libvlc_event_t *event,
                                void *data);

    void createCoreConnections();
    void removeCoreConnections();

    libvlc_media_player_t *_vlcMediaPlayer;
    libvlc_event_manager_t *_vlcEvents;

    //VlcAudio *_vlcAudio;
    VlcEqualizer *_vlcEqualizer;
};

#endif // VLCQT_MEDIAPLAYER_H_
