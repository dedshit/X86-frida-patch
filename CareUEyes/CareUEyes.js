/* Unlocked Pro features
        by dedshit
*/

const CareUEyes = Process.enumerateModules()[0];

function hex(addr) {
  return `${'0x'}${(addr).toString(16)}`;
}
function rva(addr) {
  return CareUEyes.base.add(addr);
}
function Addr(addr){
  return rva(hex(addr));
}

const mem = new Object (
  {
    TextSection: rva(0x1000),
    TextSectionSize: 3653632
  }
);

function Pro(_, __) {
  Interceptor.attach(Addr(548837), {
    onEnter(){
      Memory.protect(ptr(_), __, "rwx")
      var func_start = this.context.eip;
      var func_end = func_start.add(0x27B);
      for (let address = func_start; address <= func_end; address++) {
        if (hex(address).endsWith('6054')) {
          Memory.patchCode(ptr(address), 2, code => {
            const cw = new X86Writer(code);
            cw.putCmpRegReg("eax","eax");
            cw.flush();
          });
        }
      }
    }
  });
}
Pro(mem.TextSection, mem.TextSectionSize)