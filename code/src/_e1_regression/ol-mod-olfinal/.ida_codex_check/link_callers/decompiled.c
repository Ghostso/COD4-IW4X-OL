// 0x4eba00 @ 0x4eba00
int __cdecl sub_4EBA00(int a1)
{
  int result; // eax

  sub_4EB8B0(a1); /*0x4eba08*/
  *(_DWORD *)(a1 + 308) = 0; /*0x4eba12*/
  result = sub_74EF10(); /*0x4eba1c*/
  *(_BYTE *)(a1 + 282) |= 1u; /*0x4eba21*/
  return result; /*0x4eba28*/
}

// 0x4eba30 @ 0x4eba30
int __cdecl sub_4EBA30(int a1)
{
  int v1; // edx
  int v2; // esi
  double v3; // st7
  int v4; // edx
  float **v5; // ecx
  int v6; // edx
  float *v7; // ecx
  float *v9; // [esp+4h] [ebp-14h] BYREF
  float v10; // [esp+8h] [ebp-10h] BYREF
  float v11; // [esp+Ch] [ebp-Ch]
  float v12; // [esp+10h] [ebp-8h]

  v1 = dword_E51A84; /*0x4eba45*/
  *(float *)(a1 + 84) = 0.0; /*0x4eba4b*/
  *(_BYTE *)(a1 + 413) = 9; /*0x4eba4e*/
  *(_DWORD *)(a1 + 4) = 22; /*0x4eba55*/
  *(_DWORD *)(a1 + 308) = 0x200000; /*0x4eba5c*/
  *(_DWORD *)(a1 + 88) = 0; /*0x4eba6b*/
  *(_DWORD *)(a1 + 92) = 0; /*0x4eba6e*/
  *(_BYTE *)(a1 + 282) = 0; /*0x4eba71*/
  v10 = *(float *)(a1 + 336); /*0x4eba7d*/
  v2 = dword_E51B1C; /*0x4eba8a*/
  v11 = *(float *)(a1 + 340); /*0x4eba90*/
  v3 = *(float *)(a1 + 344); /*0x4eba93*/
  v9 = &v10; /*0x4eba9c*/
  v12 = v3; /*0x4eba9f*/
  *(_DWORD *)(a1 + 24) = (a1 + 24) ^ LODWORD(v10) ^ ~v1; /*0x4ebaa7*/
  *(_DWORD *)(a1 + 28) = (a1 + 28) ^ LODWORD(v11) ^ ~v2; /*0x4ebab6*/
  *(_DWORD *)(a1 + 32) = (a1 + 32) ^ LODWORD(v12) ^ ~dword_E51B20; /*0x4ebac5*/
  v4 = 4; /*0x4ebac7*/
  v5 = &v9; /*0x4ebacc*/
  do /*0x4ebad4*/
  {
    *(_BYTE *)v5 = 0; /*0x4ebad0*/
    v5 = (float **)((char *)v5 + 1); /*0x4ebad2*/
    --v4; /*0x4ebad3*/
  }
  while ( v4 ); /*0x4ebad4*/
  v6 = 12; /*0x4ebad6*/
  v7 = &v10; /*0x4ebadb*/
  do /*0x4ebae4*/
  {
    *(_BYTE *)v7 = 0; /*0x4ebae0*/
    v7 = (float *)((char *)v7 + 1); /*0x4ebae2*/
    --v6; /*0x4ebae3*/
  }
  while ( v6 ); /*0x4ebae4*/
  *(_DWORD *)(a1 + 12) = 0; /*0x4ebae6*/
  *(float *)(a1 + 60) = *(float *)(a1 + 348); /*0x4ebaef*/
  *(float *)(a1 + 64) = *(float *)(a1 + 352); /*0x4ebaf8*/
  *(float *)(a1 + 68) = *(float *)(a1 + 356); /*0x4ebb01*/
  *(_DWORD *)(a1 + 48) = 0; /*0x4ebb04*/
  return sub_74EF10(); /*0x4ebb10*/
}

// 0x4ecf10 @ 0x4ecf10
int __usercall sub_4ECF10@<eax>(_DWORD *a1@<esi>)
{
  int result; // eax

  a1[60] = 0; /*0x4ecf12*/
  a1[61] = 0; /*0x4ecf18*/
  a1[62] = 0; /*0x4ecf1e*/
  a1[63] = 0; /*0x4ecf24*/
  a1[64] = 0; /*0x4ecf2a*/
  a1[65] = 0; /*0x4ecf30*/
  a1[66] = 0; /*0x4ecf36*/
  a1[67] = 0; /*0x4ecf3e*/
  result = sub_4ECC00(a1); /*0x4ecf44*/
  if ( !a1[96] ) /*0x4ecf49*/
    return sub_74EF10(); /*0x4ecf54*/
  return result; /*0x4ecf59*/
}

