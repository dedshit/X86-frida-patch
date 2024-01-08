/*
  No more Trial Check & Useless FullScreen by Default
            By Dedshit
*/
const MedCalc = Process.enumerateModules()[0];

function rva(addr) {
  return MedCalc.base.add(addr);
}

const Text = new Object (

    {
      Section: rva(0x1000),
      SectionSize: 2527232,
      TrialFunc: rva(0x1083F3)
    }

)

medcalc(Text.Section, Text.SectionSize, Text.TrialFunc)
FullScreen(Text.Section, Text.SectionSize)

function medcalc(TextSection, TextSectionSize, address) {

  Interceptor.attach(address, {

    onEnter () {
      Memory.protect(TextSection, TextSectionSize, "rwx")
      Memory.patchCode(address.add(0x127), 5, function(code) {
        const _ = new X86Writer(code);
        _.putNop();
        _.flush();
      })
    },

    onLeave () {
      Memory.protect(TextSection, TextSectionSize, "rx")
    }

  });

}

function FullScreen(TextSection, TextSectionSize, address=rva(0x48DE)) {
  
  Interceptor.attach(address, {

    onEnter () {
      Memory.protect(TextSection, TextSectionSize, "rwx")
      Memory.writeByteArray(address.add(0x107), [0x83, 0x3D, 0x20, 0x73, 0x6A, 0x00, 0x00])
    },

    onLeave () {
      Memory.protect(TextSection, TextSectionSize, "rx")
    }

  });
}

