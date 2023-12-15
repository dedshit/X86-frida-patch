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

ADDR.set(Addr(1947440), {
  onEnter: function (_args) {
    Memory.scan(EASEUS_PDF_EDITOR.base, EASEUS_PDF_EDITOR.size, '80 BF  8B 00 00 00  00', {
      onMatch: (address, _size) => {
        if (address.toString().slice(-4) === 'BB29'.toLowerCase()){
          console.log("PATCHING SPLIT FUNCTION");
          Memory.patchCode(address, 3, function(code){
            const cw = new X86Writer(code);
            cw.putBytes([0x80, 0xBF, 0x8B, 0x00, 0x00, 0x00, 0x01]);
            cw.flush();
          });
        }
      }
    })
  }
});

for (const [addr, conf] of ADDR.entries()){
  Interceptor.attach(addr, conf);
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