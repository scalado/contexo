@ECHO NOTE: Microsoft Macro Assembler, does not seem to honor the /Fo flag, thus contexo cannot use assembler in Visual Studio 2005
ctx buildcomp hello -b msvc-example.bc -e msvc.env -o release
