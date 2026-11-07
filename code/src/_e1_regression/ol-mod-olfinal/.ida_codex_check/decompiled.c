// 0x5f95b0 @ 0x5f95b0
BOOL __cdecl sub_5F95B0(_DWORD *a1, int a2)
{
  int v2; // ebx
  int v3; // eax
  int v4; // edi
  int v5; // eax
  _DWORD *v6; // esi
  const char *v7; // eax
  const char *v8; // eax
  int v9; // ecx
  signed int v10; // kr00_4
  signed int v11; // eax
  signed int v12; // esi
  _DWORD *v13; // ecx
  int v14; // eax
  int *v15; // eax
  int v16; // edx
  signed int v17; // edx
  int v18; // eax
  _DWORD *v19; // ebx
  const char *v20; // eax
  int *v21; // edi
  int v22; // eax
  int v23; // esi
  char *v24; // edx
  char v25; // cl
  int v26; // edi
  int v27; // edx
  char v28; // al
  int v29; // eax
  signed int v30; // ecx
  _DWORD *v31; // eax
  bool v32; // zf
  _DWORD *v33; // ebx
  int v34; // ecx
  int v35; // edx
  const char *v36; // eax
  _DWORD *v37; // esi
  int v38; // ecx
  int v39; // edi
  char v40; // al
  int v41; // eax
  int v42; // eax
  int v43; // edx
  _DWORD *v44; // esi
  int v45; // eax
  int v46; // edx
  int v48; // esi
  char *v49; // edx
  char v50; // cl
  int *v51; // edi
  int v52; // ecx
  int i; // esi
  char v54; // al
  signed int v55; // eax
  int v56; // [esp+10h] [ebp-818h] BYREF
  int v57; // [esp+14h] [ebp-814h]
  _DWORD *v58; // [esp+18h] [ebp-810h]
  _DWORD *v59; // [esp+1Ch] [ebp-80Ch]
  char v60[2]; // [esp+41Eh] [ebp-40Ah] BYREF
  char Destination; // [esp+420h] [ebp-408h] BYREF
  _BYTE Src[1022]; // [esp+421h] [ebp-407h] BYREF
  char v63; // [esp+81Fh] [ebp-9h]

  v2 = dword_82E1358; /*0x5f95c7*/
  v58 = a1; /*0x5f95cd*/
  v3 = *(_DWORD *)(dword_82E1358 + 192); /*0x5f95d3*/
  v59 = (_DWORD *)dword_82E1358; /*0x5f95db*/
  switch ( v3 ) /*0x5f95f1*/
  {
    case 0: /*0x5f95f1*/
    case 4: /*0x5f95f1*/
    case 9: /*0x5f95f1*/
    case 10: /*0x5f95f1*/
    case 11: /*0x5f95f1*/
    case 14: /*0x5f95f1*/
    case 16: /*0x5f95f1*/
    case 17: /*0x5f95f1*/
    case 18: /*0x5f95f1*/
    case 22: /*0x5f95f1*/
    case 23: /*0x5f95f1*/
      v4 = *(_DWORD *)(dword_82E1358 + 312); /*0x5f95f8*/
      v57 = v4; /*0x5f95fe*/
      if ( !v4 || !*(_DWORD *)(dword_82E1358 + 276) && !*(_DWORD *)(dword_82E1358 + 292) ) /*0x5f9616*/
        return 0; /*0x5f961c*/
      MEMORY[0xC42DE0](&Destination, 0, 1024); /*0x5f9630*/
      v5 = *(_DWORD *)(v2 + 292); /*0x5f9635*/
      if ( v5 ) /*0x5f9640*/
      {
        v6 = v58 + 672; /*0x5f9650*/
        if ( !(unsigned __int8)sub_75E710(v58 + 672, v5, &v56) || !&v6[3 * v56] ) /*0x5f9670*/
          return 0; /*0x5f9675*/
        v7 = (const char *)sub_75E830(); /*0x5f9688*/
        MEMORY[0xC3C740](&Destination, v7, 1023); /*0x5f969a*/
        v63 = 0; /*0x5f969f*/
      }
      else
      {
        v8 = (const char *)sub_76F360(); /*0x5f96a9*/
        MEMORY[0xC3C740](&Destination, v8, 1023); /*0x5f96bb*/
        v63 = 0; /*0x5f96c0*/
      }
      v9 = (int)Src; /*0x5f96cc*/
      v10 = strlen(&Destination); /*0x5f96d0*/
      v11 = *(_DWORD *)(v4 + 16); /*0x5f96d7*/
      v12 = v10; /*0x5f96da*/
      if ( v11 ) /*0x5f96de*/
      {
        if ( v10 > v11 ) /*0x5f96e2*/
        {
          v13 = v59; /*0x5f96ea*/
          v12 = *(_DWORD *)(v4 + 16); /*0x5f96f0*/
          v14 = *v58; /*0x5f96f2*/
          Src[v12 - 1] = 0; /*0x5f96f4*/
          v15 = &v13[v14 + 77]; /*0x5f96fc*/
          v9 = *(_DWORD *)(v4 + 16); /*0x5f9703*/
          if ( *v15 > v9 ) /*0x5f9708*/
            *v15 = v9; /*0x5f970a*/
        }
      }
      v16 = a2; /*0x5f970c*/
      if ( (a2 & 0x400) != 0 ) /*0x5f9715*/
      {
        v17 = a2 & 0xFFFFFBFF; /*0x5f971b*/
        a2 = v17; /*0x5f9721*/
        if ( v17 == 8 ) /*0x5f9727*/
        {
          v18 = v59[*v58 + 77]; /*0x5f973b*/
          if ( v18 > 0 ) /*0x5f9744*/
            MEMORY[0xC3E400](&Src[v18 - 2], &Src[v18 - 1], v12 - v18 + 1); /*0x5f9754*/
          if ( v59[73] ) /*0x5f9762*/
          {
            sub_75E9A0(); /*0x5f9773*/
            v19 = v59; /*0x5f9778*/
          }
          else
          {
            v19 = v59; /*0x5f9786*/
            sub_771680(&Destination, 3); /*0x5f9791*/
            v20 = (const char *)sub_76F360(); /*0x5f979c*/
            MEMORY[0xC3C740](&Destination, v20, 1023); /*0x5f97ae*/
            v63 = 0; /*0x5f97b6*/
          }
          v21 = &v19[*v58 + 77]; /*0x5f97c2*/
          v22 = *v21; /*0x5f97c9*/
          v23 = -1; /*0x5f97cb*/
          if ( *v21 ) /*0x5f97c9*/
          {
            v24 = &v60[v22]; /*0x5f97d2*/
            do /*0x5f981e*/
            {
              if ( !v23 ) /*0x5f97db*/
                break; /*0x5f97db*/
              if ( v22 >= 2 /*0x5f980d*/
                && v24
                && v60[v22] == 94
                && (v25 = v60[v22 + 1]) != 0
                && v25 != 94
                && (v25 >= 48 && v25 <= 57 || v25 == 97) )
              {
                v22 -= 2; /*0x5f9811*/
                v24 -= 2; /*0x5f9814*/
              }
              else
              {
                --v22; /*0x5f9819*/
                --v24; /*0x5f981a*/
                ++v23; /*0x5f981b*/
              }
            }
            while ( v22 ); /*0x5f981e*/
          }
LABEL_35:
          *v21 = v22; /*0x5f9820*/
          sub_5F9530(&Destination); /*0x5f9833*/
          return 1; /*0x5f9e5a*/
        }
        v26 = v59[47]; /*0x5f9846*/
        if ( v26 == 16 ) /*0x5f984f*/
        {
          if ( !(unsigned __int8)sub_774530(v9) ) /*0x5f985a*/
            return 1; /*0x5f985a*/
          v17 = a2; /*0x5f9860*/
        }
        if ( v17 < 32 || v17 == 64 && v26 != 22 ) /*0x5f9874*/
          return 1; /*0x5f9874*/
        if ( v26 == 9 ) /*0x5f987d*/
        {
          v9 = v17 - 48; /*0x5f987f*/
          if ( (unsigned int)(v17 - 48) > 9 ) /*0x5f9884*/
            return 0; /*0x5f9884*/
        }
        if ( v26 == 17 ) /*0x5f988d*/
        {
          if ( (unsigned int)(v17 - 48) > 9 ) /*0x5f9895*/
          {
            v9 = (char)sub_4FED80(v9); /*0x5f989c*/
            if ( v27 != v9 ) /*0x5f98a1*/
              return 0; /*0x5f98a1*/
          }
          v28 = sub_4FED80(v9); /*0x5f98a7*/
          if ( v17 == v28 ) /*0x5f98b1*/
          {
            a2 = 46; /*0x5f98b3*/
            v17 = 46; /*0x5f98ba*/
          }
        }
        if ( v26 == 18 ) /*0x5f98c0*/
        {
          a2 = MEMORY[0xC40458](v17); /*0x5f98cb*/
          LOBYTE(v17) = a2; /*0x5f98ce*/
        }
        v29 = *v58; /*0x5f98d6*/
        if ( dword_7508CB4[842 * *v58] ) /*0x5f98e0*/
        {
          v34 = *(_DWORD *)(v57 + 16); /*0x5f997d*/
          if ( v34 && v59[v29 + 77] >= v34 ) /*0x5f9991*/
          {
            if ( *(_DWORD *)(v57 + 20) && sub_5FA640(v58, v59[60], 0) && (unsigned __int8)sub_5F93A0() ) /*0x5f99c1*/
              dword_82E1358 = v35; /*0x5f99ce*/
            return 1; /*0x5f99d4*/
          }
        }
        else
        {
          if ( v12 == 255 ) /*0x5f98f3*/
            return 1; /*0x5f98f3*/
          v30 = *(_DWORD *)(v57 + 16); /*0x5f98ff*/
          if ( v30 ) /*0x5f9904*/
          {
            if ( v12 >= v30 ) /*0x5f9908*/
              return 1; /*0x5f9908*/
          }
          MEMORY[0xC3E400](&Src[v59[v29 + 77]], &Src[v59[v29 + 77] - 1], v12 - v59[v29 + 77] + 1); /*0x5f992f*/
          LOBYTE(v17) = a2; /*0x5f9934*/
        }
        v31 = v59; /*0x5f9940*/
        v32 = v59[73] == 0; /*0x5f9946*/
        Src[v59[*v58 + 77] - 1] = v17; /*0x5f9956*/
        if ( v32 ) /*0x5f995d*/
        {
          v33 = v31; /*0x5f99df*/
          sub_771680(&Destination, 3); /*0x5f99ea*/
          v36 = (const char *)sub_76F360(); /*0x5f99f5*/
          MEMORY[0xC3C740](&Destination, v36, 1023); /*0x5f9a07*/
          v63 = 0; /*0x5f9a0f*/
        }
        else
        {
          sub_75E9A0(); /*0x5f9967*/
          v33 = v59; /*0x5f996c*/
        }
        v37 = v58; /*0x5f9a13*/
        v38 = v33[*v58 + 77]; /*0x5f9a22*/
        v39 = 1; /*0x5f9a24*/
        v56 = (int)&v33[*v58 + 77]; /*0x5f9a29*/
        while ( 1 ) /*0x5f9a30*/
        {
          for ( ; &Src[v38 - 1]; v38 += 2 ) /*0x5f9a30*/
          {
            if ( Src[v38 - 1] != 94 ) /*0x5f9a45*/
              break; /*0x5f9a45*/
            v40 = Src[v38]; /*0x5f9a47*/
            if ( !v40 || v40 == 94 ) /*0x5f9a54*/
              break; /*0x5f9a54*/
            if ( (v40 < 48 || v40 > 57) && v40 != 97 ) /*0x5f9a60*/
              break; /*0x5f9a60*/
          }
          if ( !Src[v38 - 1] || !v39 ) /*0x5f9a77*/
            break; /*0x5f9a77*/
          ++v38; /*0x5f9a79*/
          --v39; /*0x5f9a7a*/
        }
        *(_DWORD *)v56 = v38; /*0x5f9a83*/
        sub_5F9530(&Destination); /*0x5f9a90*/
        v41 = *(_DWORD *)(v57 + 16); /*0x5f9a9b*/
        if ( v41 ) /*0x5f9aa3*/
        {
          if ( v33[*v37 + 77] >= v41 ) /*0x5f9aae*/
          {
            if ( *(_DWORD *)(v57 + 20) ) /*0x5f9ab0*/
            {
              v42 = sub_5FA640(v37, v33[60], 0); /*0x5f9ac0*/
              *(_DWORD *)(v42 + 4 * *v37 + 308) = 0; /*0x5f9acc*/
              if ( v42 ) /*0x5f9ad9*/
              {
                if ( (unsigned __int8)sub_5F93A0() ) /*0x5f9adb*/
                  dword_82E1358 = v43; /*0x5f9ae4*/
              }
            }
          }
        }
        v16 = a2; /*0x5f9aea*/
      }
      else
      {
        switch ( a2 ) /*0x5f9b36*/
        {
          case 162: /*0x5f9b36*/
          case 193: /*0x5f9b36*/
            v55 = v59[*v58 + 77]; /*0x5f9df6*/
            if ( v55 < v12 ) /*0x5f9dff*/
            {
              MEMORY[0xC3E400](&Src[v55 - 1], &Src[v55], v12 - v55); /*0x5f9e14*/
              if ( v59[73] ) /*0x5f9e22*/
                sub_75E9A0(); /*0x5f9e33*/
              else
                sub_771680(&Destination, 3); /*0x5f9e4b*/
            }
            return 1; /*0x5f9e38*/
          case 157: /*0x5f9b36*/
          case 187: /*0x5f9b36*/
            v51 = &v59[*v58 + 77]; /*0x5f9d72*/
            v52 = *v51; /*0x5f9d79*/
            for ( i = 1; ; --i ) /*0x5f9d7b*/
            {
              for ( ; &Src[v52 - 1]; v52 += 2 ) /*0x5f9d80*/
              {
                if ( Src[v52 - 1] != 94 ) /*0x5f9d95*/
                  break; /*0x5f9d95*/
                v54 = Src[v52]; /*0x5f9d97*/
                if ( !v54 || v54 == 94 ) /*0x5f9da4*/
                  break; /*0x5f9da4*/
                if ( (v54 < 48 || v54 > 57) && v54 != 97 ) /*0x5f9db0*/
                  break; /*0x5f9db0*/
              }
              if ( !Src[v52 - 1] || !i ) /*0x5f9dc7*/
                break; /*0x5f9dc7*/
              ++v52; /*0x5f9dc9*/
            }
            *v51 = v52; /*0x5f9dd3*/
            sub_5F9530(&Destination); /*0x5f9dde*/
            return 1; /*0x5f9de6*/
          case 156: /*0x5f9b36*/
          case 185: /*0x5f9b36*/
            v21 = &v59[*v58 + 77]; /*0x5f9ce8*/
            v22 = *v21; /*0x5f9cef*/
            v48 = -1; /*0x5f9cf1*/
            if ( *v21 ) /*0x5f9cef*/
            {
              v49 = &v60[v22]; /*0x5f9cf8*/
              do /*0x5f9d44*/
              {
                if ( !v48 ) /*0x5f9d01*/
                  break; /*0x5f9d01*/
                if ( v22 >= 2 /*0x5f9d33*/
                  && v49
                  && v60[v22] == 94
                  && (v50 = v60[v22 + 1]) != 0
                  && v50 != 94
                  && (v50 >= 48 && v50 <= 57 || v50 == 97) )
                {
                  v22 -= 2; /*0x5f9d37*/
                  v49 -= 2; /*0x5f9d3a*/
                }
                else
                {
                  --v22; /*0x5f9d3f*/
                  --v49; /*0x5f9d40*/
                  ++v48; /*0x5f9d41*/
                }
              }
              while ( v22 ); /*0x5f9d44*/
            }
            goto LABEL_35; /*0x5f9d44*/
          case 165: /*0x5f9b36*/
          case 182: /*0x5f9b36*/
            v59[*v58 + 77] = 0; /*0x5f9ccb*/
            *(_DWORD *)(v4 + 28) = 0; /*0x5f9cd2*/
            return 1; /*0x5f9cd5*/
          case 166: /*0x5f9b36*/
          case 188: /*0x5f9b36*/
            v59[*v58 + 77] = v12; /*0x5f9c9e*/
            sub_5F9530(&Destination); /*0x5f9cae*/
            return 1; /*0x5f9cb6*/
          case 161: /*0x5f9b36*/
          case 192: /*0x5f9b36*/
            dword_7508CB4[842 * *v58] = dword_7508CB4[842 * *v58] == 0; /*0x5f9bcf*/
            return 1; /*0x5f9bd1*/
        }
      }
      switch ( v16 ) /*0x5f9af0*/
      {
        case 9: /*0x5f9af0*/
          if ( dword_750943C ) /*0x5f9afd*/
          {
LABEL_86:
            v44 = v59; /*0x5f9b03*/
            v45 = sub_5FA2C0(v58, v59[60]); /*0x5f9b17*/
            goto LABEL_105; /*0x5f9b1f*/
          }
          break;
        case 154: /*0x5f9af0*/
        case 183: /*0x5f9af0*/
          goto LABEL_86; /*0x5f9be8*/
        case 155: /*0x5f9af0*/
        case 189: /*0x5f9af0*/
          break;
        default:
          v44 = v59; /*0x5f9c36*/
          goto LABEL_110; /*0x5f9c36*/
      }
      v44 = v59; /*0x5f9bfe*/
      v45 = sub_5FA640(v58, v59[60], 1); /*0x5f9c14*/
LABEL_105:
      if ( v45 && (unsigned __int8)sub_5F93A0() ) /*0x5f9c22*/
        dword_82E1358 = v46; /*0x5f9c2b*/
      v16 = a2; /*0x5f9c31*/
LABEL_110:
      if ( (v16 == 13 || v16 == 191) && v44[66] ) /*0x5f9c49*/
      {
        sub_5F7680(v58, v44, v44[66]); /*0x5f9c5c*/
        v16 = a2; /*0x5f9c61*/
      }
      return v16 != 13 && v16 != 191 && v16 != 27; /*0x5f9c77*/
    default:
      return 0;
  }
}

// 0x5fad00 @ 0x5fad00
const _OVERLAPPED *__cdecl sub_5FAD00(const _OVERLAPPED **a1, bool *a2)
{
  int v2; // esi
  const _OVERLAPPED *result; // eax
  int v4; // eax
  const _OVERLAPPED *v5; // eax
  int v6; // edi
  int v7; // ebx
  int v8; // ecx
  const _OVERLAPPED *v9; // eax
  int v10; // ecx
  int v11; // edi
  int v12; // edx
  int Internal_low; // esi
  int v14; // ebx
  int v15; // [esp+4h] [ebp-28h]
  char *String; // [esp+8h] [ebp-24h]
  const _OVERLAPPED *v17; // [esp+Ch] [ebp-20h]
  int v18; // [esp+10h] [ebp-1Ch]
  int v19; // [esp+14h] [ebp-18h]
  const _OVERLAPPED *v20; // [esp+18h] [ebp-14h]
  const _OVERLAPPED *v21; // [esp+1Ch] [ebp-10h]
  const _OVERLAPPED *v22; // [esp+20h] [ebp-Ch]
  int v23; // [esp+24h] [ebp-8h]
  int v24; // [esp+28h] [ebp-4h] BYREF

  v2 = 0; /*0x5fad11*/
  *a1 = 0; /*0x5fad18*/
  *a2 = 0; /*0x5fad1a*/
  v24 = 0; /*0x5fad1d*/
  result = (const _OVERLAPPED *)sub_76B7A0("mp/loadingScreenBGM.csv", &v24); /*0x5fad20*/
  if ( v24 )
  {
    v4 = sub_76F190("ui_gametype"); /*0x5fad37*/
    if ( v4 )
    {
      if ( *(_BYTE *)(v4 + 8) == 6 )
        v5 = *(_DWORD *)(v4 + 60) ? *(const _OVERLAPPED **)(*(_DWORD *)(v4 + 64) + 4 * *(_DWORD *)(v4 + 12)) : &Mask;
      else
        v5 = *(const _OVERLAPPED **)(v4 + 12); /*0x5fad6a*/
      v22 = v5; /*0x5fad6d*/
    }
    else
    {
      v22 = &Mask; /*0x5fad45*/
    }
    result = (const _OVERLAPPED *)sub_76F190("ui_mapname"); /*0x5fad75*/
    if ( result )
    {
      if ( LOBYTE(result->Offset) == 6 )
        result = result[3].Internal ? *(const _OVERLAPPED **)(result[3].InternalHigh + 4 * result->OffsetHigh) : &Mask;
      else
        result = (const _OVERLAPPED *)result->OffsetHigh; /*0x5fada6*/
      v21 = result; /*0x5fada9*/
    }
    else
    {
      v21 = &Mask; /*0x5fad81*/
    }
    v6 = v24; /*0x5fadad*/
    v7 = *(_DWORD *)(v24 + 8); /*0x5fadb0*/
    v8 = 0; /*0x5fadb3*/
    v15 = v7; /*0x5fadb5*/
    v19 = 0; /*0x5fadb8*/
    if ( v7 > 0 ) /*0x5fadbd*/
    {
      v23 = *(_DWORD *)(v24 + 4); /*0x5fadc6*/
      v18 = 0; /*0x5fadc9*/
      while ( 2 ) /*0x5fadea*/
      {
        if ( v23 <= 0 || v8 >= v7 || v8 < 0 || (v9 = *(const _OVERLAPPED **)(v2 + *(_DWORD *)(v6 + 12))) == 0 ) /*0x5fadea*/
          v9 = &Mask; /*0x5fadec*/
        if ( v23 <= 1 || v8 >= v7 || v8 < 0 || (v20 = *(const _OVERLAPPED **)(*(_DWORD *)(v6 + 12) + v2 + 8)) == 0 ) /*0x5fae0a*/
          v20 = &Mask; /*0x5fae0c*/
        if ( v23 <= 2 || v8 >= v7 || v8 < 0 || (v17 = *(const _OVERLAPPED **)(*(_DWORD *)(v6 + 12) + v2 + 16)) == 0 ) /*0x5fae2d*/
          v17 = &Mask; /*0x5fae2f*/
        if ( v23 <= 3 || v8 >= v7 || v8 < 0 || (String = *(char **)(*(_DWORD *)(v6 + 12) + v2 + 24)) == 0 ) /*0x5fae50*/
          String = (char *)&Mask; /*0x5fae52*/
        v10 = 0x7FFFFFFF; /*0x5fae5c*/
        v11 = (char *)v22 - (char *)v9; /*0x5fae61*/
        do /*0x5fae63*/
        {
          v12 = *((char *)&v9->Internal + v11); /*0x5fae63*/
          Internal_low = SLOBYTE(v9->Internal); /*0x5fae67*/
          v14 = v10; /*0x5fae6a*/
          v9 = (const _OVERLAPPED *)((char *)v9 + 1); /*0x5fae6c*/
          --v10; /*0x5fae6d*/
          if ( !v14 ) /*0x5fae70*/
            break; /*0x5fae70*/
          if ( v12 != Internal_low ) /*0x5fae74*/
          {
            if ( 2 * (v12 >= Internal_low) != 1 ) /*0x5fae89*/
              goto LABEL_48; /*0x5fae89*/
            break; /*0x5fae89*/
          }
        }
        while ( v12 ); /*0x5fae63*/
        if ( !sub_774710(v21, v20) ) /*0x5fae9d*/
        {
          *a1 = v17; /*0x5faed3*/
          result = (const _OVERLAPPED *)MEMORY[0xC3C234](String); /*0x5faed5*/
          *a2 = result != 0; /*0x5faee5*/
          return result; /*0x5faee5*/
        }
LABEL_48:
        v7 = v15; /*0x5fae9f*/
        result = (const _OVERLAPPED *)(8 * v23); /*0x5faeaf*/
        v8 = v19 + 1; /*0x5faeb1*/
        v2 = 8 * v23 + v18; /*0x5faeb2*/
        v19 = v8; /*0x5faeb4*/
        v18 = v2; /*0x5faeb7*/
        if ( v8 < v15 ) /*0x5faebc*/
        {
          v6 = v24; /*0x5fadd0*/
          continue; /*0x5fadd0*/
        }
        break;
      }
    }
  }
  return result; /*0x5faec4*/
}

