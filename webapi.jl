include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs

println("Inicializando modelo...")
model = initialize_model()
println("Modelo creado con éxito")

# Variable para controlar cuándo hacer step
last_step_time = time()
step_interval = 0.1  # Hacer step cada 100ms como máximo

# Inicializar/actualizar llaves desde Python
route("/init_keys", method = POST) do
    try
        payload = jsonpayload()
        key_positions = payload["keys"]  # Lista de tuplas [(x,y), (x,y), ...]
        
        # Limpiar modelo actual
        global model
        model = initialize_model(key_positions=[(Int(k[1]), Int(k[2])) for k in key_positions])
        
        @info "Llaves inicializadas (escondidas): $key_positions"
        json(Dict("status" => "ok", "keys" => key_positions))
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

println("Servidor iniciando en puerto 8000...")
up(8000, host="0.0.0.0")