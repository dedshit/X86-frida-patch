/* UNLIMITED Trial & Nag removed
        by dedshit
*/


const PROXIFIER = Process.enumerateModules()[0];

function hex(addr) {
  return `${'0x'}${(addr).toString(16)}`;
}

function rva(addr) {
  return PROXIFIER.base.add(addr);
}


const Text = new Object (

  {
    Section: rva(0x1000), 
    SectionSize: 2486272,
    Nag: rva(0x6E2D0),
    Trialfunc: rva(0x71230)
  }

)

TrialPatch(Text.Section, Text.SectionSize, Text.Trialfunc)

function NagScreenPatch(TextSection, TextSectionSize, address) {

    Memory.protect(ptr(TextSection), TextSectionSize, "rwx")
    Memory.patchCode(ptr(address.add(0x892)), 5, function(code){
        const _ = new X86Writer(code);
        _.putBytes([0x90, 0x90, 0x90, 0x90, 0x90]);
        _.flush();
    })

    Memory.patchCode(ptr(address.add(0x8C4)), 6, function(code){
        const _ = new X86Writer(code);
        _.putBytes([0x0F, 0x85, 0xD6, 0xFE, 0xFF, 0xFF]);
        _.flush();
    })
    Memory.protect(ptr(TextSection), TextSectionSize, "rx")

}

NagScreenPatch(Text.Section, Text.SectionSize, Text.Nag)


function TrialPatch(TextSection, TextSectionSize, address) {

  Interceptor.attach(ptr(address), {

    onEnter(){

      Memory.protect(ptr(TextSection), TextSectionSize, "rwx")
      var func_start = this.context.eip;
      var func_end = this.context.eip.add(0x95);
      for (let address = func_start; address <= func_end; address++) {

        if (hex(address).endsWith('1283')) {

          Memory.patchCode(ptr(hex(address)), 5, function(code){
            const Years = new X86Writer(code);
            Years.putMovRegU32('eax', 4258265604)
            Years.flush();
          });
        }

        else if (hex(address).endsWith('1271')) {

          Memory.patchCode(ptr(hex(address)), 5, function(code){
            const Days = new X86Writer(code);
            Days.putMovRegU32('eax', 768486)
            Days.flush();
          });
        }

      }

    },

    onLeave(){

      Memory.protect(ptr(TextSection), TextSectionSize, "rx")

    }

  });
}