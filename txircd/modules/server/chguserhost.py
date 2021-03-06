from twisted.plugin import IPlugin
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class ServerChgHost(ModuleData, Command):
	implements(IPlugin, IModuleData, ICommand)
	
	name = "ServerChangeHost"
	core = True
	
	def actions(self):
		return [ ("updatehost", 10, self.propagateChangeHost) ]
	
	def serverCommands(self):
		return [ ("CHGHOST", 1, self) ]
	
	def propagateChangeHost(self, user, hostType, oldHost, newHost, fromServer = None):
		if newHost is not None:
			apply = (user.host() == newHost)
			self.ircd.broadcastToServers(fromServer, "CHGHOST", user.uuid, hostType, "1" if apply else "0", newHost, prefix=self.ircd.serverID)
		else:
			self.ircd.broadcastToServers(fromServer, "CHGHOST", user.uuid, user.currentHostType(), "1", user.host(), prefix=self.ircd.serverID)
			self.ircd.broadcastToServers(fromServer, "CHGHOST", user.uuid, hostType, "1", "*", prefix=self.ircd.serverID)
	
	def parseParams(self, server, params, prefix, tags):
		if len(params) != 4:
			return None
		if params[0] not in self.ircd.users:
			if params[0] in self.ircd.recentlyQuitUsers:
				return {
					"lostuser": True
				}
			return None
		newHost = params[3]
		if newHost == "*":
			newHost = None
		return {
			"user": self.ircd.users[params[0]],
			"type": params[1],
			"apply": (params[2] == "1"),
			"host": newHost
		}
	
	def execute(self, server, data):
		if "lostuser" in data:
			return True
		apply = data["apply"]
		newHost = data["host"]
		if newHost is None:
			data["user"].resetHost(data["type"])
		elif apply:
			data["user"].changeHost(data["type"], newHost, server)
		else:
			data["user"].updateHost(data["type"], data["host"], server)
		return True

chgHost = ServerChgHost()