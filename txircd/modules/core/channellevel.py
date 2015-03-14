from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implements

class ChannelLevel(ModuleData):
	implements(IModuleData)
	
	name = "ChannelLevel"
	core = True
	
	def actions(self):
		return [ ("checkchannellevel", 1, self.levelCheck),
		         ("checkexemptchanops", 1, self.exemptCheck) ]
	
	def minLevelFromConfig(self, configKey, checkType, defaultLevel):
		configLevel = self.ircd.config.get(configKey, {}).get(checkType, defaultLevel)
		try:
			minLevel = int(configLevel)
		except ValueError:
			if configLevel not in self.ircd.channelStatuses:
				return False # If the status doesn't exist, then, to be safe, we must assume NOBODY is above the line.
			minLevel = self.ircd.channelStatuses[configLevel][1]
		return minLevel
	
	def levelCheck(self, levelType, channel, user):
		minLevel = self.minLevelFromConfig("channel_minimum_level", levelType, 100)
		return channel.userRank(user) >= minLevel
	
	def exemptCheck(self, exemptType, channel, user):
		minLevel = self.minLevelFromConfig("channel_exempt_level", exemptType, 0)
		if not minLevel:
			return False # No minimum level == no exemptions
		return channel.userRank(user) >= minLevel

chanLevel = ChannelLevel()