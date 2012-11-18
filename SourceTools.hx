
import neko.Lib;
import haxe.macro.Context;
import haxe.macro.Compiler;
import haxe.macro.Type;

@macro class SourceTools {
	public inline static function print( str ){
		Lib.print(str);
		Lib.print("\n");
	}

	public static function complete(){
		trace("here");
		Context.onGenerate( onGenerate );
		var ty = Context.getType('Test2');
		switch(ty){
			case TInst(t,params): 
				var cl = t.get();
				trace("class "+cl.name);
				trace(cl.pos);

				var constr = cl.constructor.get();
				if( constr != null ){
					trace("constructor "+constr.name);
					trace(constr.pos.min + "=>" + constr.pos.max);
				}

				for( f in cl.fields.get() ){
					trace("field "+f.name);
					trace(f.pos);
				}
			default: 
				print("invalid"); 
				trace(ty);
		}
	}	

	static function onGenerate( types : Array<Type> ){
		for( t in types ){
			Lib.print( t );
		} 
	}
}