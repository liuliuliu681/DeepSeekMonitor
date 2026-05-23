import os
import random
import sys

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPoint,
    QPropertyAnimation, QSequentialAnimationGroup, Qt, QTimer, QUrl,
)
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QLabel


def _app_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


ASSETS_DIR = os.path.join(_app_dir(), "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")


class BalanceAnimator:
    """Drives spend (fly-away) and income (coin-fall) animations."""

    def __init__(self, parent):
        self._parent = parent
        self._active: list = []
        self._sprites: list[QLabel] = []
        self._timers: list[QTimer] = []

        self._sound_spend = self._load_sound("spend.WAV")
        self._sound_income = self._load_sound("income.WAV")

        self.animations_enabled = True
        self.sound_enabled = True

    # ── public API ──────────────────────────────────────────────

    def play_decrease(self):
        if not self.animations_enabled:
            return
        self._clear()
        self._play_sound(self._sound_spend)
        self._animate_fly_away()

    def play_increase(self):
        if not self.animations_enabled:
            return
        self._clear()
        self._play_sound(self._sound_income)
        self._animate_coin_fall()

    # ── internal helpers ────────────────────────────────────────

    def _load_sound(self, filename):
        path = os.path.join(SOUNDS_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            effect.setVolume(0.7)
            return effect
        except Exception:
            return None

    def _play_sound(self, effect):
        if not self.sound_enabled or effect is None:
            return
        try:
            effect.play()
        except Exception:
            pass

    def _clear(self):
        for t in self._timers:
            try:
                t.stop()
            except Exception:
                pass
        self._timers.clear()

        for anim in self._active:
            try:
                anim.stop()
            except Exception:
                pass
        self._active.clear()

        for sprite in self._sprites:
            try:
                sprite.hide()
            except Exception:
                pass
            try:
                sprite.deleteLater()
            except Exception:
                pass
        self._sprites.clear()

    # ── fly-away (spend) ────────────────────────────────────────

    def _animate_fly_away(self):
        pixmap = QPixmap(os.path.join(IMAGES_DIR, "flying_money.png"))
        if pixmap.isNull():
            return

        parent_rect = self._parent.rect()

        sprite = QLabel(self._parent)
        sprite.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        sprite.setFixedSize(80, 80)
        sprite.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        start_x = (parent_rect.width() - 80) // 2
        start_y = parent_rect.height() // 3
        sprite.move(start_x, start_y)
        sprite.show()

        opacity = QGraphicsOpacityEffect(sprite)
        opacity.setOpacity(1.0)
        sprite.setGraphicsEffect(opacity)

        pos_anim = QPropertyAnimation(sprite, b"pos")
        pos_anim.setDuration(2000)
        pos_anim.setStartValue(QPoint(start_x, start_y))
        pos_anim.setEndValue(QPoint(start_x, start_y - 180))
        pos_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        fade_anim = QPropertyAnimation(opacity, b"opacity")
        fade_anim.setDuration(2000)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)

        group = QParallelAnimationGroup()
        group.addAnimation(pos_anim)
        group.addAnimation(fade_anim)

        def on_finished():
            try:
                self._active.remove(group)
            except ValueError:
                pass
            try:
                self._sprites.remove(sprite)
            except ValueError:
                pass
            sprite.deleteLater()

        group.finished.connect(on_finished)
        group.start()

        self._active.append(group)
        self._sprites.append(sprite)

    # ── coin fall (income) ──────────────────────────────────────

    def _animate_coin_fall(self):
        pixmap = QPixmap(os.path.join(IMAGES_DIR, "coin.png"))
        if pixmap.isNull():
            return

        coin_size = 40
        parent_rect = self._parent.rect()
        parent_width = parent_rect.width()
        parent_height = parent_rect.height()
        count = 10

        for i in range(count):
            start_x = random.randint(10, max(10, parent_width - coin_size - 10))
            start_y = -random.randint(20, 120)

            sprite = QLabel(self._parent)
            sprite.setPixmap(pixmap.scaled(coin_size, coin_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            sprite.setFixedSize(coin_size, coin_size)
            sprite.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            sprite.move(start_x, start_y)
            sprite.show()

            opacity = QGraphicsOpacityEffect(sprite)
            opacity.setOpacity(1.0)
            sprite.setGraphicsEffect(opacity)

            fall_duration = 4000 + random.randint(0, 800)
            end_y = parent_height - random.randint(10, 60)
            wobble_amplitude = random.randint(15, 40)
            half = (start_y + end_y) / 2

            pos_anim = QPropertyAnimation(sprite, b"pos")
            pos_anim.setDuration(fall_duration)
            pos_anim.setStartValue(QPoint(start_x, start_y))
            pos_anim.setKeyValueAt(0.25, QPoint(start_x + wobble_amplitude, start_y + (end_y - start_y) * 0.25))
            pos_anim.setKeyValueAt(0.5, QPoint(start_x - wobble_amplitude + random.randint(-10, 10), half))
            pos_anim.setKeyValueAt(0.75, QPoint(start_x + wobble_amplitude // 2, start_y + (end_y - start_y) * 0.75))
            pos_anim.setEndValue(QPoint(start_x, end_y))
            pos_anim.setEasingCurve(QEasingCurve.Type.InQuad)

            fade_anim = QPropertyAnimation(opacity, b"opacity")
            fade_anim.setDuration(fall_duration)
            fade_anim.setStartValue(1.0)
            fade_anim.setKeyValueAt(0.6, 1.0)
            fade_anim.setEndValue(0.0)

            group = QParallelAnimationGroup()
            group.addAnimation(pos_anim)
            group.addAnimation(fade_anim)

            def make_cleanup(g, s):
                def cleanup():
                    try:
                        self._active.remove(g)
                    except ValueError:
                        pass
                    try:
                        self._sprites.remove(s)
                    except ValueError:
                        pass
                    s.deleteLater()
                return cleanup

            group.finished.connect(make_cleanup(group, sprite))

            self._active.append(group)
            self._sprites.append(sprite)

            delay = i * random.randint(100, 500)
            if delay > 0:
                timer = QTimer(self._parent)
                timer.setSingleShot(True)

                def make_timer_cb(t, g):
                    def on_timeout():
                        g.start()
                        try:
                            self._timers.remove(t)
                        except ValueError:
                            pass
                        t.deleteLater()
                    return on_timeout

                timer.timeout.connect(make_timer_cb(timer, group))
                timer.start(delay)
                self._timers.append(timer)
            else:
                group.start()
