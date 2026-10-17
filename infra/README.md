# Infraestructura en AWS

Cuenta del perfil `default`, región `us-east-1`. Todo lleva el tag `Project=ya-sale`.

## Qué se crea

```
Internet ──► App Runner (1 instancia, 1 vCPU / 2 GB) ──VPC connector──► subredes privadas
                                                                          ├─► RDS Postgres 16 (db.t4g.micro, privado)
                                                                          └─► NAT gateway ──► Tavily, Exa, Claude
```

- **Base privada:** RDS sin acceso público. Su security group solo acepta el puerto 5432
  desde el security group del conector de App Runner.
- **Salida a internet:** un NAT gateway, para que el servicio llegue a Tavily, Exa y Claude.
- **Secretos:** las claves y el `DATABASE_URL` viven en SSM Parameter Store (`/ya-sale/*`,
  SecureString). El servicio los lee con su propio rol, limitado a `/ya-sale/*`. Ningún
  script imprime un secreto.
- **Imagen:** ECR `ya-sale`, con escaneo al subir.

## Pasos

```bash
bash infra/setup.sh            # una vez: red, base, ECR, roles, sal de huellas
bash infra/secrets.sh          # cuando backend/.env tenga las tres claves y la base esté lista
bash infra/deploy.sh <tag>     # cada deploy: build, push, servicio, prueba de humo
```

## Costo aproximado

- NAT gateway: unos USD 1,1 por día, más el tráfico.
- RDS `db.t4g.micro`: unos USD 0,4 por día.
- App Runner (1 vCPU / 2 GB, siempre activo): unos USD 1,5 por día.
- SSM estándar y ECR: centavos.

## Después del evento

Borrar el servicio de App Runner, el NAT gateway (y liberar su IP elástica) y la instancia
RDS. Son los que cobran por hora.
