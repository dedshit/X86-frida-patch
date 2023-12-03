
/* Patch both Nag dialog & Trial limitations
        by dedshit
*/
let module = Process.enumerateModules()[0];
let Patches = [
	{Nag: '81 ?? 77 ?? 00 00'},
	{Nag: '0F ?? ?? 00 00 00'}
]

const addrs = ["0x7ff655e80385", "0x7ff655e804d6"];
for (let instructionPatch of Patches) {
	Memory.scan(module.base, module.size, instructionPatch.Nag, {
		onMatch: function(address, size){
			let res = String(address);
			if (res === addrs[1]) {
				Memory.patchCode(ptr(addrs[1]), size, code => {
            				const cw = new X86Writer(code);
					cw.putBytes([0x81, 0xFB, 0x77, 0x01, 0x00, 0x00]);
            				cw.flush();
        			});
			}
			Memory.patchCode(ptr(addrs[0]), size, code => {
            			const cw = new X86Writer(code);
            			cw.putBytes([0xE9, 0xE7, 0x00, 0x00, 0x00, 0x00]);
            			cw.flush();
        		});
		},
		onError: function(reason){
			console.warn('Error: ' + reason);
		},
        onComplete: function(){
			console.log("patched");
		}
	});
}