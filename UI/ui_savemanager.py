# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_savemanager.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSplitter, QWidget)

class Ui_SaveManagerDialog(object):
    def setupUi(self, SaveManagerDialog):
        if not SaveManagerDialog.objectName():
            SaveManagerDialog.setObjectName(u"SaveManagerDialog")
        SaveManagerDialog.resize(200, 250)
        SaveManagerDialog.setWindowTitle(u"window.save_manager")
        self.listWidget = QListWidget(SaveManagerDialog)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setGeometry(QRect(10, 10, 181, 201))
        self.splitter = QSplitter(SaveManagerDialog)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setGeometry(QRect(10, 220, 181, 23))
        self.splitter.setOrientation(Qt.Horizontal)
        self.loadButton = QPushButton(self.splitter)
        self.loadButton.setObjectName(u"loadButton")
        self.loadButton.setText(u"button.load")
        self.splitter.addWidget(self.loadButton)
        self.deleteButton = QPushButton(self.splitter)
        self.deleteButton.setObjectName(u"deleteButton")
        self.deleteButton.setText(u"button.delete")
        self.splitter.addWidget(self.deleteButton)
        self.cancelButton = QPushButton(self.splitter)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setText(u"button.cancel")
        self.splitter.addWidget(self.cancelButton)

        self.retranslateUi(SaveManagerDialog)

        QMetaObject.connectSlotsByName(SaveManagerDialog)
    # setupUi

    def retranslateUi(self, SaveManagerDialog):
        pass
    # retranslateUi

