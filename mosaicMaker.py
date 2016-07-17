import wx
import scipy.misc as im
import numpy as np
from os import listdir
import random
import time

def applyBasepicHue((pxlImg, perc, gridColour)):
   return (1.0-perc)*pxlImg + perc*gridColour

class mosaicSeq():
    def __init__(self, allPicFolder, labelFile, mosaicRow, mosaicCol, imgRow, imgCol, steps, perc):
        #steps is number of intermediate pics to pass through to go from initial jumble to final basepic
        self.mosaicRow = mosaicRow; self.mosaicCol = mosaicCol
        self.imgRow = imgRow; self.imgCol = imgCol
        self.allPicFolder = allPicFolder
        self.steps = steps
        self.perc = perc
        self.labelData = {}
        for line in open(labelFile).readlines():
            parts = line.split(' ')
            self.labelData[parts[0]] = ' '.join(parts[1:])
        self.availablePxlPics = listdir(self.allPicFolder)
        random.shuffle(self.availablePxlPics)
        self.totPicsNeeded = self.mosaicRow*self.mosaicCol
        repeat = self.totPicsNeeded/len(self.availablePxlPics)
        randomPick = self.totPicsNeeded%len(self.availablePxlPics)
        self.finalList = repeat*self.availablePxlPics + self.availablePxlPics[:randomPick]
        random.shuffle(self.finalList)
        self.allImgData = {picName:im.imresize(im.imread(self.allPicFolder + picName), (self.imgRow,self.imgCol))/255.0 for picName in self.availablePxlPics[:(randomPick,None)[repeat>0]]}
        self.numUniqueImgs = len(self.allImgData)
        self.mosaicSeqImageLoc = []

    def getMosiacLabel(self):
        self.mosiacLabel = [[self.labelData.get(self.finalList[r*self.mosaicCol + c], '') for c in range(self.mosaicCol)] for r in range(self.mosaicRow)]

    def getPxlPics(self, basepic, step):
        mosiacData = [[None for c in range(self.mosaicCol)] for r in range(self.mosaicRow)]
        p = step * (self.perc/float(self.steps))
        print 'getPxlPics: step:',step
        if True: #multiprocessing is slowing it down. sticking to serial
            mosiacData = [[applyBasepicHue((self.allImgData[self.finalList[r*self.mosaicCol + c]], p, basepic[r,c])) for c in range(self.mosaicCol)] for r in range(self.mosaicRow)]
        else:
            from multiprocessing import Pool
            pool = Pool(8)
            args = [(self.allImgData[self.finalList[r*self.mosaicCol + c]], p, basepic[r,c]) for r in range(self.mosaicRow) for c in range(self.mosaicCol)]                   
            for imgId, temparray in enumerate(pool.imap(applyBasepicHue, args)):
                mosiacData[imgId/self.mosaicCol][imgId%self.mosaicCol] = temparray
            pool.close(); pool.join()
        return mosiacData

    def generateMosaicImages(self, step, dumpLoc, mosiacData):
        mosaicImg = np.zeros((self.mosaicRow*self.imgRow, self.mosaicCol*self.imgCol, 3))
        for mosaicRow in range(self.mosaicRow):
            for mosaicCol in range(self.mosaicCol):
                mosaicImg[mosaicRow*self.imgRow:(mosaicRow+1)*self.imgRow, mosaicCol*self.imgRow:(mosaicCol+1)*self.imgCol, :] = mosiacData[mosaicRow][mosaicCol]
        d = dumpLoc + str(step) + '.jpg'
        im.imsave(d, mosaicImg)
        self.mosaicSeqImageLoc.append(d)

    def generateNewMosiacSeq(self, basepicLoc, dumpLoc):      
        basepic = im.imresize(im.imread(basepicLoc), (self.mosaicRow,self.mosaicCol))/255.0
        self.getMosiacLabel()
        for step in range(self.steps+1):
            self.generateMosaicImages(step, dumpLoc, self.getPxlPics(basepic, step))


class displayImage(wx.Frame):
    def __init__(self, parent, id, loc, name, label):
        selectedImage = wx.Image(loc+name).ConvertToBitmap()
        wx.Frame.__init__(self,parent,id,name,size=(selectedImage.GetWidth(),selectedImage.GetHeight()))
        self.static_bitmap = wx.StaticBitmap(self,wx.NewId(), bitmap=selectedImage)
        #place caption correctly. maybe place it below the pic
        print label.strip('\n')
        
        box = wx.BoxSizer(wx.VERTICAL)
        if label.strip('\n') != '':
            self.static_text = wx.StaticText(self, 2, ' '+label.strip('\n')+' ', pos=wx.Point(0,selectedImage.GetHeight()-100))
            self.static_text.SetForegroundColour((0,0,0))
            self.static_text.SetBackgroundColour((150,150,150))
            font = wx.Font(22, wx.TELETYPE, wx.NORMAL, wx.BOLD)
            self.static_text.SetFont(font)
            box.Add(self.static_text, 2, wx.EXPAND)

        box.Add(self.static_bitmap, 1, wx.EXPAND)
        wx.EVT_LEFT_DOWN(self.static_bitmap, self.onClick)  #register mouse click event

    def onClick(self,event):
        self.Destroy()  #for closing when clicked


class displayMosaic(wx.Frame):
    def __init__(self, parent, id, name, allPicFolder, labelFile, mosaicRow, mosaicCol, imgRow, imgCol, steps, perc, basepicLoc, dumpLoc, interval):
        wx.Frame.__init__(self,parent,id,name)  #size=(imgRow*mosaicRow, imgCol*mosaicCol)
        self.mosaicRow = mosaicRow; self.mosaicCol = mosaicCol
        self.allPicFolder = allPicFolder
        start = time.time()
        m = mosaicSeq(allPicFolder, labelFile, mosaicRow, mosaicCol, imgRow, imgCol, steps, perc)
        m.generateNewMosiacSeq(basepicLoc, dumpLoc)
        self.numUniqueImgs = m.numUniqueImgs
        self.imagesNames = m.finalList
        self.seenImages = {}
        print 'preprocessing time:', time.time()-start
        self.imagesToDisplay = m.mosaicSeqImageLoc
        self.labelsToDisplay = m.mosiacLabel
        self.origImages = m.finalList
        self.displayImageId = 0
        
        self.static_bitmap = wx.StaticBitmap(self,wx.NewId(), bitmap=wx.EmptyBitmap(300, 300))
        self.static_bitmap.SetCursor(wx.CROSS_CURSOR)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.static_bitmap, 1, wx.EXPAND)
        
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Layout()

        wx.EVT_LEFT_DOWN(self.static_bitmap, self.onClick)  #register mouse click event

        self.slideTimer = wx.Timer(None)  #set timer to andle trasition
        self.slideTimer.Bind(wx.EVT_TIMER, self.transition)
        self.slideTimer.Start(interval)

        self.mode = 1  #in transition mode

    def transition(self, event):
        #print self.imagesToDisplay[self.displayImageId]
        self.displayImage(self.imagesToDisplay[self.displayImageId])
        self.displayImageId += 1
        if self.displayImageId >= len(self.imagesToDisplay):
            self.slideTimer.Stop()
            self.mode = 0  #now no longer in transition mode

    def displayImage(self, imgName):
        im = wx.Image(imgName)
        self.tw = self.static_bitmap.GetSize().GetWidth()
        self.th = self.static_bitmap.GetSize().GetHeight()
        self.static_bitmap.SetBitmap(im.Rescale(self.tw,self.th).ConvertToBitmap())

    def onClick(self,event):
        if self.mode == 0:
            x = event.GetX(); y = event.GetY()
            mosaicRowSpan = self.th/float(self.mosaicRow)
            mosaicColSpan = self.tw/float(self.mosaicCol)
            r = int(y/mosaicRowSpan)
            c = int(x/mosaicColSpan)
            self.seenImages[self.imagesNames[r*self.mosaicCol + c]] = self.seenImages.get(self.imagesNames[r][c],0)+1

            imgFrame = displayImage(None, wx.ID_ANY, self.allPicFolder, self.origImages[r*self.mosaicCol + c], self.labelsToDisplay[r][c])
            #print self.origImages[:self.mosaicCol]
            imgFrame.Show(True)
            self.SetTitle('Mosaic:' + str(len(self.seenImages)) + '/' + str(self.numUniqueImgs))



if __name__ == '__main__':
    app = wx.App(False)
    
    allPicFolder = 'pixelPics/'
    labelFile = 'caption.txt'
    basepicLoc = 'basepic.jpg'
    dumpLoc = ''
    interval = 1000
    frame = displayMosaic(None, wx.ID_ANY, 'Mosaic', allPicFolder, labelFile, 150, 150, 15, 15, 5, 0.7, basepicLoc, dumpLoc, interval)
    #frame = displayMosaic(None, wx.ID_ANY, 'Mosaic', allPicFolder, labelFile, 50, 25, 20, 20, 2, 0.7, basepicLoc, dumpLoc, interval)
    
    frame.Show(True)
    frame.Maximize(True)
    app.MainLoop()