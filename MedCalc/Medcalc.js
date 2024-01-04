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
