from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from txircd.utils import ircLower
from zope.interface import implements

class ServerQuit(ModuleData):
	implements(IPlugin, IModuleData)
	
	name = "ServerQuit"
	core = True
	
	def actions(self):
		return [ ("serverquit", 1, self.sendSQuit),
		         ("commandpermission-SQUIT", 1, self.restrictSQuit) ]
	
	def userCommands(self):
		return [ ("SQUIT", 1, UserSQuit(self.ircd)) ]
	
	def serverCommands(self):
		return [ ("SQUIT", 1, ServerSQuit(self.ircd)),
		         ("RSQUIT", 1, RemoteSQuit(self.ircd)) ]
	
	def sendSQuit(self, server, reason):
		if not server.bursted:
			if server.serverID:
				server.sendMessage("SQUIT", server.serverID, reason, prefix=server.nextClosest)
			return
		closestHop = server
		while closestHop.nextClosest != self.ircd.serverID:
			closestHop = self.ircd.servers[closestHop.nextClosest]
		if closestHop == server:
			closestHop = None
		self.ircd.broadcastToServers(closestHop, "SQUIT", server.serverID, reason, prefix=server.nextClosest)
	
	def restrictSQuit(self, user, data):
		if not self.ircd.runActionUntilValue("userhasoperpermission", user, "command-squit", users=[user]):
			user.sendMessage(irc.ERR_NOPRIVILEGES, "Permission denied - You do not have the correct operator privileges")
			return False
		return None

class UserSQuit(Command):
	implements(ICommand)
	
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, user, params, prefix, tags):
		if len(params) < 2:
			user.sendSingleError("SQuitParams", irc.ERR_NEEDMOREPARAMS, "SQUIT", "Not enough parameters")
			return None
		source = self.ircd.serverID
		if params[0] not in self.ircd.serverNames:
			if ircLower(params[0]) == ircLower(self.ircd.name):
				user.sendSingleError("SQuitTarget", irc.ERR_NOSUCHSERVER, self.ircd.name, "You can't unlink this server from itself")
				return None
			user.sendSingleError("SQuitTarget", irc.ERR_NOSUCHSERVER, params[0], "No such server")
			return None
		return {
			"source": source,
			"target": self.ircd.servers[self.ircd.serverNames[params[0]]],
			"reason": params[1]
		}
	
	def execute(self, user, data):
		targetServer = data["target"]
		reason = data["reason"]
		
		if targetServer.nextClosest == self.ircd.serverID:
			targetServer.disconnect(reason)
			user.sendMessage("NOTICE", "*** Disconnected {}".format(targetServer.name))
		else:
			targetServer.sendMessage("RSQUIT", targetServer.serverID, reason, prefix=self.ircd.serverID)
			user.sendMessage("NOTICE", "*** Sent remote SQUIT for {}".format(targetServer.name))
		return True

class ServerSQuit(Command):
	implements(ICommand)
	
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, server, params, prefix, tags):
		if len(params) != 2:
			return None
		targetServerID = params[0]
		if targetServerID == self.ircd.serverID:
			targetServerID = prefix
		if targetServerID not in self.ircd.servers:
			if targetServerID in self.ircd.recentlyQuitServers:
				return {
					"lostserver": True
				}
			return None
		return {
			"target": self.ircd.servers[targetServerID],
			"reason": params[1]
		}
	
	def execute(self, server, data):
		if "lostserver" not in data:
			data["target"].disconnect("Received SQUIT from remote server: {}".format(data["reason"]))
		return True

class RemoteSQuit(Command):
	implements(ICommand)
	
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, server, params, prefix, tags):
		if len(params) != 2:
			return None
		if params[0] not in self.ircd.servers:
			if params[0] in self.ircd.recentlyQuitServers:
				return {
					"lostserver": True
				}
			return None
		return {
			"target": self.ircd.servers[params[0]],
			"reason": params[1]
		}
	
	def execute(self, server, data):
		if "lostserver" in data:
			return True
		targetServer = data["target"]
		if targetServer.nextClosest == self.ircd.serverID:
			targetServer.disconnect(data["reason"])
			return True
		targetServer.sendMessage("RSQUIT", targetServer.serverID, data["reason"], prefix=targetServer.nextClosest)
		return True

squit = ServerQuit()