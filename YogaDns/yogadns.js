/* UNLIMITED Trial & Nag removed
        by dedshit
*/


const YogaDns = Process.enumerateModules()[0];

function hex(addr) {
  return `${'0x'}${(addr).toString(16)}`;
}

function rva(addr) {
  return YogaDns.base.add(addr);
}


const Text = new Object (

  {
    Section: rva(0x1000),
    SectionSize: 3416064,
    address: rva(0x85CF0)
  }

)

TrialPatch(Text.Section, Text.SectionSize, Text.address)

function TrialPatch(TextSection, TextSectionSize, address) {

    Interceptor.attach(ptr(address), {
    onEnter(){
      Memory.protect(ptr(TextSection), TextSectionSize, "rwx")
      var func_start = this.context.eip;
      var func_end = this.context.eip.add(0xA1);
      for (let address = func_start; address <= func_end; address++) {
          if (hex(address).endsWith('5d2f')) {
              Memory.writeByteArray(ptr(hex(address)), [0xB8, 0x89, 0xA2, 0x0A, 0x00, 0x90])
          } else if (hex(address).endsWith('5d3f')) {
              Memory.writeByteArray(ptr(hex(address)), [0x88, 0x4F, 0x08])
          } else if (hex(address).endsWith('5d42')) {
              Memory.writeByteArray(ptr(hex(address)), [0xB8, 0x04, 0xFA, 0xCF, 0xFD, 0x90])
          }
      }
    },
    onLeave(){
      Memory.protect(ptr(TextSection), TextSectionSize, "rx")
    }
  });
}