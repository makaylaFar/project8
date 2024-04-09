from direct.interval.LerpInterval import LerpFunc
from direct.gui.OnscreenImage import OnscreenImage
from direct.particles.ParticleEffect import ParticleEffect
# regex module import for string editing.
import re
from collideObjectBase import *
from direct.task import Task
from typing import Callable
from panda3d.core import *
from random import *


class spaceShip(SphereCollideObject):
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, texPath: str, posVec: Vec3, scaleVec: float, task, render, accept: Callable[[str, Callable], None], traverser: CollisionTraverser):
        super(spaceShip, self).__init__(loader, modelPath, parentNode, nodeName, 0, 2)
        self.taskManager = task
        self.render = render
        self.accept = accept                                                                                            
        self.loader = loader

        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setName(nodeName)

        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)
        self.SetKeyBindings()

        self.reloadTime = .25
        self.missileDistance = 4000 # until it explodes
        self.missileBay = 1 # only 1 missile in the bay to be
        self.ParticleEffectTime = .3
        self.SetParticles()

        self.traverser = traverser

        #self.traverser = CollisionTraverser()
        self.handler = CollisionHandlerEvent()

        self.handler.addInPattern('into')
        self.accept('into', self.HandleInto)

        self.taskManager.add(self.CheckIntervals, 'checkMissiles', 34)
        self.cntExplode = 0
        self.explodeIntervals = {}

        self.fireSound = loader.loadSfx("./assets/soundEffects/pew-pew.mp3")
        self.fireSound.setVolume(0.5)

        self.enableHUD()

    def CheckIntervals(self, task):
        for i in Missile.Intervals:
            #isPlaying returns true or false to see if the missile has gotten to the end of its path.
            if not Missile.Intervals[i].isPlaying():
                # if its path is done, we get rid of everything to do with that missile.
                Missile.cNodes[i].detachNode()
                Missile.fireModels[i].detachNode()

                del Missile.Intervals[i]
                del Missile.fireModels[i]
                del Missile.cNodes[i]
                del Missile.collisionSolids[i]
                print(i + ' has reached the end of its fire solution.')

                # we break because whn things are deleted from a dictionary, we have to refactor the dictionary so we can reuse it. This is because when we delete things, there's a gap at that point.
                break
        return Task.cont

    def SetKeyBindings(self):
        self.accept("w", self.Thrust, [1])
        self.accept("w-up", self.Thrust, [0])

        self.accept("a", self.LeftTurn, [1])
        self.accept("a-up", self.LeftTurn, [0])

        self.accept("d", self.RightTurn, [1])
        self.accept("d-up", self.RightTurn, [0])

        self.accept("shift", self.MoveUp, [1])
        self.accept("shift-up", self.MoveUp, [0])

        self.accept("enter", self.MoveDown, [1])
        self.accept("enter-up", self.MoveDown, [0])

        self.accept("arrow_left", self.RollLeft, [1])
        self.accept("arrow_left-up", self.RollLeft, [0])

        self.accept("arrow_right", self.RollRight, [1])
        self.accept("arrow_right-up", self.RollRight, [0])

        self.accept('f', self.Fire)

    def Thrust(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyThrust, 'forward-thrust')
        else:
            self.taskManager.remove('forward-thrust')


    def ApplyThrust(self, task):
        rate = 10
        trajectory = self.render.getRelativeVector(self.modelNode, Vec3.forward())
        trajectory.normalize()
        self.modelNode.setFluidPos(self.modelNode.getPos() + trajectory * rate)
        return Task.cont

    def LeftTurn(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyLeftTurn, 'left-turn')

        else:
            self.taskManager.remove('left-turn')
    
    def ApplyLeftTurn(self, task):
        #half a degree every frame
        rate = .5
        self.modelNode.setH(self.modelNode.getH() + rate)
        return Task.cont
    
    def RightTurn(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyRightTurn, 'right-turn')

        else:
            self.taskManager.remove('right-turn')
    
    def ApplyRightTurn(self, task):
        #half a degree every frame
        rate = -0.5
        self.modelNode.setH(self.modelNode.getH() + rate)
        return Task.cont
    
    def MoveUp(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyMoveUp, 'upward-thrust')
        else:
            self.taskManager.remove('upward-thrust')

    
    def ApplyMoveUp(self, task):
        rate = .6
        self.modelNode.setP(self.modelNode.getP() + rate)
        return Task.cont
    
    def MoveDown(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyMoveDown, 'downward-thrust')
        else:
            self.taskManager.remove('downward-thrust')

    
    def ApplyMoveDown(self, task):
        rate = -.6
        self.modelNode.setP(self.modelNode.getP() + rate)
        return Task.cont
    
    def RollLeft(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyRollLeft, 'left-roll')
        else:
            self.taskManager.remove('left-roll')

    
    def ApplyRollLeft(self, task):
        rate = .6
        self.modelNode.setR(self.modelNode.getR() + rate)
        return Task.cont
    
    def RollRight(self, keyDown):
        if keyDown:
            self.taskManager.add(self.ApplyRollRight, 'right-roll')
        else:
            self.taskManager.remove('right-roll')

    
    def ApplyRollRight(self, task):
        rate = .6
        self.modelNode.setR(self.modelNode.getR() - rate)
        return Task.cont
    
    def Fire(self):
        if self.missileBay:
            travRate = self.missileDistance
            aim = self.render.getRelativeVector(self.modelNode, Vec3.forward()) # fires in direction ship is facing

            # Normalizing a vector makes it consistent all the time
            aim.normalize()

            fireSolution = aim * travRate
            InFront = aim * 150
            travVec = fireSolution + self.modelNode.getPos()
            self.missileBay -= 1
            tag ='Missile' + str(Missile.missileCount)

            posVec = self.modelNode.getPos() + InFront # spawn the missile in front of the nose of the ship

            #create our missile
            currentMissile = Missile(self.loader, './assets/phaser/phaser.egg', self.render, tag, posVec, 4.0)

            # "fluid = 1" makes collision be checked between the last interval and this interval to make sure theres nothing in-between both chcecks thath wasn't hit.
            Missile.Intervals[tag] = currentMissile.modelNode.posInterval(2.0, travVec, startPos = posVec, fluid = 1)
            Missile.Intervals[tag].start()

            self.traverser.addCollider(currentMissile.collisionNode, self.handler)
            self.fireSound.play()

        else:
            # if we aren't reloading, we want to start reloading.
            if not self.taskManager.hasTaskNamed('reload'):
                print('Initializing reload...')
                # call the reload method on no delay.
                self.taskManager.doMethodLater(0, self.Reload, 'reload')
                return Task.cont
            
    def HandleInto(self, entry):
        fromNode= entry.getFromNodePath().getName()
        print("fromNode: " + fromNode)
        intoNode = entry.getIntoNodePath().getName()
        print("intoNode: " + intoNode)

        intoPosition = Vec3(entry.getSurfacePoint(self.render))

        tempVar = fromNode.split('_')   
        shooter = tempVar[0]
        tempVar = intoNode.split('-')
        tempVar = intoNode.split('_')
        #tempVar = intoNode.split('ship')
        victim = tempVar[0]

        pattern = r'[0-9]'
        strippedString = re.sub(pattern, '', victim)

        if (strippedString == "Drone"):
            print(shooter + ' is DONE.')
            Missile.Intervals[shooter].finish()
            print(victim, ' hit at ', intoPosition)
            self.DroneDestroy(victim, intoPosition)

            #self.Explode(intoPosition)

        elif strippedString == "Planet":
            Missile.Intervals[shooter].finish()
            self.PlanetDestroy(victim)

        elif strippedString == "Space Station":
            Missile.Intervals[shooter].finish()
            self.SpaceStationDestroy(victim)
        

        else:
            Missile.Intervals[shooter].finish()
            
    def DroneDestroy(self, hitID, hitPosition):
        # unity also has a find method, yet it is very inefficeint if used anywhere but at the beginning of the program.
        nodeID = self.render.find(hitID)
        nodeID.detachNode()

        # start the explosion
        self.explodeNode.setPos(hitPosition)
        self.Explode(hitPosition)

    def PlanetDestroy(self, victim: NodePath):
        nodeID = self.render.find(victim)

        self.taskManager.add(self.PlanetShrink, name = "PlanetShrink", extraArgs = [nodeID], appendTask = True)

    def SpaceStationDestroy(self, victim: NodePath):
        nodeID = self.render.find(victim)
        self.taskManager.add(self.SpaceStationShrink, name = "SpaceStationShrink", extraArgs = [nodeID], appendTask = True)

    def Explode(self, impactPoint):
        self.cntExplode += 1
        tag = 'particles-' + str(self.cntExplode)

        self.explodeIntervals[tag] = LerpFunc(self.ExplodeLight, fromData = 0, toData = 1, duration = 4.0, extraArgs = [impactPoint])
        self.explodeIntervals[tag].start()

    def ExplodeLight(self, t, explosionPosition):
        #self.SetParticles()
        
        if t == 1.0 and self.explodeEffect:
            self.explodeEffect.disable()

        elif t == 0:
            self.explodeEffect.start(self.explodeNode)

    def SetParticles(self):
        base.enableParticles()
        self.explodeEffect = ParticleEffect()
        self.explodeEffect.loadConfig("./assets/particlefx/SP21-explosionIII.ptf")
        self.explodeEffect.setScale(20)
        self.explodeNode = self.render.attachNewNode('ExplosionEffects')


    def Reload(self, task):
        if task.time > self.reloadTime:
            self.missileBay += 1
            if self.missileBay > 1:
                self.missileBay = 1
            print ("Reload complete.")
            return Task.done
            
        elif task.time <= self.reloadTime:
            print("reload proceeding...")

            return Task.cont
    
    def enableHUD(self):
        self.Hud = OnscreenImage(image = "./assets/hud/crossHair.png")

        self.Hud.setTransparency(TransparencyAttrib.MAlpha)

    def PlanetShrink(self, nodeID: NodePath, task):
        if task.time < 2.0:
            if nodeID.getBounds().getRadius() > 0:
                scaleSubtraction = 10
                nodeID.setScale(nodeID.getScale() - scaleSubtraction)
                temp = 30 * random.random()
                nodeID.setH(nodeID.getH() + temp)
                return task.cont
            
        else:
            nodeID.detachNode()
            return task.done
        
    def SpaceStationShrink(self, nodeID: NodePath, task):
        if task.time < 2.0:
            if nodeID.getBounds().getRadius() > 0:
                scaleSubtraction = 2
                nodeID.setScale(nodeID.getScale() - scaleSubtraction)
                temp = 30 * random.random()
                nodeID.setH(nodeID.getH() + temp)
                return task.cont
            
        else:
            nodeID.detachNode()
            return task.done

class Missile(SphereCollideObject):
    fireModels = {}
    cNodes = {}
    collisionSolids = {}
    Intervals = {}
    missileCount = 0

    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, posVec: Vec3, scaleVec: float = 1.0):
        super(Missile, self).__init__(loader, modelPath, parentNode, nodeName, Vec3(0,0,0), 3.0)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setPos(posVec)

        Missile.missileCount += 1

        Missile.fireModels[nodeName] = self.modelNode
        Missile.cNodes[nodeName] = self.collisionNode

        # we retrieve the solid for our collisionNode.
        Missile.collisionSolids[nodeName] = self.collisionNode.node().getSolid(0)
        Missile.cNodes[nodeName].show()

        print ("fire Torpedo #" + str(Missile.missileCount))
