include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs

println("Inicializando modelo...")
model = initialize_model()
println("Modelo creado con éxito")

# Variable para controlar cuándo hacer step
last_step_time = time()
step_interval = 0.05  # Hacer step cada 100ms como máximo

# Inicializar/actualizar llaves desde Python
route("/init_keys", method = POST) do
    try
        payload = jsonpayload()
        key_data = payload["keys"]  # Lista de diccionarios con pos + estados
        
        # Limpiar modelo actual
        global model
        
        # Convertir datos y crear llaves con sus estados iniciales
        key_positions = []
        key_states = []
        
        for k in key_data
            # 🔧 CORRECCIÓN: JSON convierte índices a strings
            # Acceder con strings y convertir a Int
            pos_array = k["pos"]
            pos = (Int(pos_array[1]), Int(pos_array[2]))
            push!(key_positions, pos)
            
            # Acceder a booleanos (estos sí vienen correctos)
            is_hidden = Bool(k["is_hidden"])
            is_visible = Bool(k["is_visible"])
            push!(key_states, (is_hidden, is_visible))
            
            estado = is_visible ? "VISIBLE" : "escondida"
            @info "Procesando llave en $pos - Estado: $estado"
        end
        
        model = initialize_model(
            key_positions=key_positions, 
            key_states=key_states
        )
        
        @info "Llaves inicializadas correctamente"
        json(Dict("status" => "ok", "keys" => key_data))
    catch e
        @error "Error en /init_keys" exception=e
        json(Dict("error" => string(e)))
    end
end

# **NUEVA RUTA**: Hacer visible una llave escondida
route("/reveal_key", method = POST) do
    try
        payload = jsonpayload()
        key_pos = (Int(payload["x"]), Int(payload["y"]))
        
        # Encontrar y revelar la llave
        for agent in allagents(model)
            if agent isa Key && agent.pos == key_pos && agent.is_hidden
                agent.is_hidden = false
                agent.is_visible = true
                @info "Llave en $key_pos ahora es VISIBLE (fantasma la perseguirá)"
                break
            end
        end
        
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /reveal_key" exception=e
        json(Dict("error" => string(e)))
    end
end

# Actualizar estado: llave recolectada
route("/collect_key", method = POST) do
    try
        payload = jsonpayload()
        key_pos = (Int(payload["x"]), Int(payload["y"]))
        
        # Marcar la llave como recolectada
        for agent in allagents(model)
            if agent isa Key && agent.pos == key_pos
                agent.is_visible = false
                agent.is_collected = true
                @info "Llave en $key_pos RECOLECTADA (fantasma dejará de perseguirla)"
                break
            end
        end
        
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /collect_key" exception=e
        json(Dict("error" => string(e)))
    end
end

# Ruta principal que Python consulta
route("/update") do
    try
        global last_step_time
        
        # Solo hacer step si ha pasado suficiente tiempo
        current_time = time()
        if current_time - last_step_time >= step_interval
            step!(model, 1)
            last_step_time = current_time
        end
        
        # Obtener posiciones RÁPIDAMENTE
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]

        json(Dict(
            "ghosts" => ghosts,
            "keys" => keys
        ))
    catch e
        @error "Error en /update" exception=e
        json(Dict("error" => string(e)))
    end
end

# Ruta de status (sin step)
route("/status") do
    try
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys_visible = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]
        keys_hidden = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_hidden]
        keys_collected = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_collected]

        json(Dict(
            "ghosts" => ghosts,
            "keys_visible" => keys_visible,
            "keys_hidden" => keys_hidden,
            "keys_collected" => keys_collected
        ))
    catch e
        @error "Error en /status" exception=e
        json(Dict("error" => string(e)))
    end
end


Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

# ⚡ CONFIGURACIÓN DE TIMEOUTS
#Genie.config.server_timeout = 30
#Genie.config.server_keepalive_timeout = 30

#Genie.config.server_timeout = 60

println("Servidor iniciando en puerto 8000...")
println("Endpoints disponibles:")
println("  - GET  http://localhost:8000/update")
println("  - GET  http://localhost:8000/status")
println("  - POST http://localhost:8000/init_keys")
println("  - POST http://localhost:8000/reveal_key")
println("  - POST http://localhost:8000/collect_key")

println("Servidor iniciando en puerto 8000...")
up(8000, host="0.0.0.0")