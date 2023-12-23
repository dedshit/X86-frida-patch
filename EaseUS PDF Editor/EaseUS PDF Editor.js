/* Unlocked All Trial limitations
        by dedshit
*/

const EASEUS_PDF_EDITOR = Process.enumerateModules()[0];

function hex(addr) {
  return `${'0x'}${(addr).toString(16)}`;
}
function rva(addr) {
  return EASEUS_PDF_EDITOR.base.add(addr);
}
function Addr(addr){
  return rva(hex(addr));
}

const Mem = () => (
  {
    TextSection: rva(0x1000), 
    TextSectionSize: 3014656
  }
);

PageExtract_Pagesplit(Mem().TextSection, Mem().TextSectionSize)
Patches()
WATERMARK(0x1B2EEF, Mem().TextSection, Mem().TextSectionSize)

function Patches(){
  const ADDR = new Map();
  ADDR.set(Addr(680672), {
    onEnter: function (_args) {
      console.log("BYPASSING BATCH FILE PROCESS");
    },
    onLeave: function (retval) {
      retval.replace(0x1);
    }
  });

  ADDR.set(Addr(1160000), {
    onEnter: function (_args) {
      let counttt = 0;
      console.log("BYPASSING TRIAL NAG FROM SAVE FUNCTION");
      while(true){
        if (counttt++ === 83){
          if (Instruction.parse(Addr(1160000).add(counttt)).mnemonic === "cmp"){
            Memory.patchCode(Addr(1160000).add(counttt), 3, function(code){
            	const cw = new X86Writer(code);
              	cw.putBytes([0x38, 0x5B, 0x74]);
              	cw.flush();
            });
          }
          break;
        }
      }
    }
  });

	ADDR.set(Addr(1164560), {
    onEnter: function (_args) {
      let counttt = 0;
      console.log("Patching Digital Signature FUNCTION");
      while(true){
        if (counttt++ === 97){
          Memory.patchCode(Addr(1164560).add(counttt), 5, function(code){
            const cw = new X86Writer(code);
            cw.putTestRegReg("ecx","ecx");
            cw.flush();
          });
          break;
        }
      }
    }
  });
	
  for (const [addr, conf] of ADDR.entries()){
    Interceptor.attach(addr, conf);
  }
}

function WATERMARK(offset, txtsec, size){
  const WATERMARK = rva(offset)
  Memory.protect(ptr(txtsec), size, "rwx")
  console.log("WATERMARK patched")
  Memory.writeByteArray(WATERMARK, [0x84, 0xC9])
  Memory.protect(ptr(txtsec), size, "rx")
}

Memory.scan(EASEUS_PDF_EDITOR.base, EASEUS_PDF_EDITOR.size, '80 7D  F3  00', {
    onMatch: (address, size) => {
      if (address.toString().slice(-4) === '7f13'){
        console.log("PATCHING OCR FUNCTION");
        Memory.patchCode(address, size, code => {
          	const cw = new X86Writer(code);
       	  	cw.putBytes([0x80, 0x7D, 0x00, 0x00]);
       	  	cw.flush();
       });
      }
    }
});

function PageExtract_Pagesplit(txtsec, size){
	Memory.protect(ptr(txtsec), size, "rwx")
  Memory.scan(EASEUS_PDF_EDITOR.base, EASEUS_PDF_EDITOR.size, '80 ??  ?? ?? ?? ??  00', {
    onMatch: (address, _size) => {
      let addr = address.toString().slice(-4);
      if (addr === 'bb29'){
        console.log("PATCHING SPLIT FUNCTION");
        Memory.writeByteArray(address, [0x80, 0xBF, 0x8B, 0x00, 0x00, 0x00, 0x01]);
      } else if (addr === '0ff5'){
        console.log("PATCHING Extract FUNCTION");
        Memory.writeByteArray(address, [0x80, 0xDA, 0x8B, 0x00, 0x00, 0x00, 0x01]);
      }
    },
		
		onComplete: () => {
      Memory.protect(ptr(txtsec), size, "rx")
    }
  });
}
