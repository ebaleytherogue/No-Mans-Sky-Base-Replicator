# [No Man's Sky Base Replicator](https://github.com/ebaleytherogue/No-Mans-Sky-Base-Replicator) \- Use Cases

By ebaleytherogue

## Copying a Base to Another Location in the 256 Galaxies

Bases can be copied to any location, whether the same planet as the original, another planet in that system, another system in that galaxy, or anywhere in the other 255 galaxies.

**Caveat**: Bases need to be copied to existing base positions. This is because precise spatial coordinates (galaxy, system, planet, location on planet) need to exist as a target for the new incarnation of the base.

Note: Frequently, after you use the tool, your “new” base will not be set properly in its new home. It might be a bit underground, or floating above ground, or its tilt will not match the terrain. Perhaps even there might be sections of the base floating in the air. Don’t panic\! You can fix this easily via my  [No Man's Sky 3D Base Aligner](https://github.com/ebaleytherogue/No-Mans-Sky-3D-Base-Aligner) app.

## Shelving or Archiving Bases \- Usually Done in Order to Reclaim Space in One’s Gamesave

This feature occurred to me as I tested the basic copying features of the app. I run a very full gamesave, frequently at or near the \~400 base-per-gamesave limit, and when I copied a base, I would get the in-game message that the number of bases I had was at its limit, and/or the number of base pieces I had was at its limit.

So, I created these two mechanics in order to allow users to shelve or archive (two different things, which I will get to…) bases, removing them from the gamesave, yet with the ability to restore them later.

Think about this for a moment. To fully appreciate it, know this. When a base is removed from a gamesave, via an editor such as this one, it is done outside of the game. This means the Hello Games server has not registered a Base Deletion. Thus, your bases exist in two realities:

1) The bases in your save are the bases you can travel to and interact with, and  
2) The bases registered in the Hello Games servers are your bases that OTHERS in the game can interact with

Again, think what this means, that you can have your bases existing in the universe, and SOMEONE can see them…even if you cannot. Your work persists.

But that’s not good enough. I wanted the ability for us to be able to change our minds, restore our bases, and then have both others AND us be able to see them. This is possible if we use the ‘Shelving’ concept, but not if we use the ‘Archiving’ path. Which path one chooses is up to them. I’ve chosen both paths, depending.

### Shelving

If one shelves a base:

* The base is exported to a file on disk  
* The user is prompted to REPLACE it in the gamesave \-- using the same base name and more importantly, the same base-registration information \-- with one of three types of bases: Very simple, enclosed shelter, or an object-heavy example of one of my bases, the last one there for experimentation fun. \[The user can change in their own base templates at any time\]  
* If the user had x number of bases at the beginning of the shelving process, they still have x number of bases at the end of it.  
* So long as the user does not upload the base again, at the “new” base’s Base Computer, then the HG servers only know about the last version of the base uploaded.

The moment a base is shelved, the “new” version of that base \-- created from one of my templates \-- becomes the base the user can visit.

**Use Case:**

A traveler wishes to shed a large number of objects from their gamesave so that they can apportion that finite number to other bases, building out smaller bases with more parts.

### Archiving

If one archives a base:

* The base is exported to a file on disk  
* The user is prompted whether they wish to simply export the base (similar to what can be done in Vectorcmdr’s NMSE app) or DELETE THE BASE FROM THE SAVE.  
  * Choosing to delete the base totally removes it from the gamesave. This option leaves the base on the HG servers, but the base is now orphaned. Its creator no longer has access to it as a creator, but were they to visit the base, the base would likely still be there, and the user could interact with it as any other traveler could. **I do not see a use for this, for ME, but others might wish to do this.**  
  * Choosing to leave the base within the gamesave results in the user having a copy of the base on disk with no action taken against the gamesave.

## Archiving Bases for Storing or Sharing

Using the ‘Archive to disk but leave within the gamesave’ option, the user has an opportunity to select ALL their bases, or bases based on textual filtering, continually building the selected base set upon which the commands will act. Ie, they can creatively and efficiently pick the bases upon which they wish to affect archiving or shelving. And because we’re talking about archiving right now, observe the use case:

**Use Case:**

The user wishes to leave the bases they export within the gamesave, producing only disk files for them to share with their friends. They decide to export only bases containing ‘G001’ in their names, and of those, only those that also have the word ‘Portal’ in their names. They make those selections, archive-without-removing-from-gamesave, and they almost instantly have a folder full of exactly those bases’ .nmsbase files.